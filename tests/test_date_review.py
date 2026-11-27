"""Offline regressions for the November 20-26 audit. No live sites or API keys."""
import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from gov_report.crawl_issues import report_issues
from gov_report.crawler import GovCrawler
from gov_report.date_utils import parse_cn_date, resolve_date_range
from gov_report.llm_classifier import DateRequestBudget, LLMClassifier
from gov_report.llm_transport import ModelCallError
from gov_report.parser import LinkItem, extract_article
from gov_report.task_state import TaskState
from gov_report.classifier import classify


class DateReviewTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name)
        self.w=GovCrawler([],{},self.root,use_llm=False,use_cache=False)
        self.w.log=Mock()
        self.start,self.end=resolve_date_range(start_date="2026-11-20",end_date="2026-11-26")
        self.url="https://fixture.gov.cn/policy/notice.html"
        self.title="关于开展职务任免的通知"

    def process(self,html,list_day=None):
        self.w._memory_checkpoints.clear()  # Independent page snapshots, shared model cache.
        a=extract_article(html,self.url,self.title)
        self.w.load_article=Mock(return_value=(a,False))
        item=LinkItem(self.title,self.url,publish_date=parse_cn_date(list_day),date_reliable=bool(list_day),context="栏目:政策文件")
        self.w.verify_dates=True
        rec,_=self.w.process_candidate({"name":"fixture"},item,self.start,self.end,"政策文件",reconsider=True)
        return rec,self.w._memory_checkpoints['fixture',self.url]

    def test_audited_header_dates_and_true_in_range_control(self):
        rows=[("A34","11-24","05-25"),("A46","11-23","11-13"),("A47","11-23","09-21"),
              ("A48","11-23","11-17"),("A49","11-23","11-13"),("A50","11-23","09-21"),
              ("control","11-23","11-23")]
        for key,meta,header in rows:
            with self.subTest(key=key):
                html=(f'<meta name="PubDate" content="2026-{meta}"><h1>{self.title}</h1>'
                      f'<div>日期：<span>2026-{header} 13:22</span> 来源：官网</div><article>经研究决定，任命张某。</article>')
                rec,p=self.process(html,"2026-"+header)
                self.assertEqual(p["status"],"included" if key=="control" else "out_of_range")
                self.assertEqual(p["article"]["date_source"],"标题栏发布日期")
                if rec:
                    self.assertEqual(rec["publish_date"],"2026-11-23")

    def test_regulation_library_vs_unconfirmed_history(self):
        _,p=self.process(f"<h1>{self.title}</h1><p>2000-01-01 来源：国务院</p><article>历史法规原文。</article>")
        self.assertEqual(p["status"],"out_of_range")
        _,p=self.process("<article>根据2000-01-01的管理规定，相关手续如下。</article>")
        self.assertEqual(p["status"],"historical_hint")
        self.assertEqual(report_issues({"coverage":{"sources":[{"issues":[p]}]}}),[])
        a=extract_article('<meta name="PubDate" content="2018"><article>日期不明。</article>',
                          "https://fixture.gov.cn/xxgk2018/notice.html")
        self.assertIsNone(a.publish_date)

    def test_formal_personnel_not_generic_notice(self):
        for self.title in ("关于钱建华同志晋升职级的通知","关于黄冬生同志晋升职级、张桥同志任职的通知"):
            rec,_=self.process(f'<h1>{self.title}</h1><p>2026-11-20 来源：某厅</p><article>经研究决定，现予通知。</article>')
            self.assertEqual(rec["category"],"人事任免")

    def test_verified_model_date_and_retryable_failure(self):
        html=(f'<h1>{self.title}</h1><article>本通知已于2026-11-21在本网站首次公开。'
              '请在2026-11-26前提交全部反馈意见。</article>')
        self.w.llm=LLMClassifier(self.root/"cache.jsonl")
        def reply(payload,**options):
            rows=json.loads(payload)["日期证据"]
            key,row=next((k,r) for k,r in rows.items() if r["date"]=="2026-11-21")
            return {"id":key,"quote":row["quote"],"role":"网页发布日期"}
        with patch.object(self.w.llm,"is_available",return_value=True),patch.object(self.w.llm,"_call_api",side_effect=reply) as api:
            for _ in range(2):
                rec,_=self.process(html)
                self.assertEqual(rec["date_source"],"模型复核网页发布日期")
                self.assertEqual(rec["publish_date"],"2026-11-21")
                self.assertIn("首次公开",rec["date_review_quote"])
            self.assertEqual(api.call_count,1)
        self.w.llm.cache_enabled=False
        with patch.object(self.w.llm,"is_available",return_value=True),patch.object(self.w.llm,"_call_api",side_effect=ModelCallError("HTTP 401",kind="authentication")):
            _,p=self.process(html)
            self.assertEqual((p["status"],p["failure_kind"]),("llm_failed","date_model_failed"))

    def test_fabricated_quote_deadline_or_missing_choice_cannot_resolve(self):
        llm=LLMClassifier(cache_enabled=False)
        rows=[dict(kind="期限线索",date="2026-11-26",quote="反馈截止：2026-11-26"),
              dict(kind="正文日期线索",date="2026-11-21",quote="本通知于2026-11-21公开")]
        with patch.object(llm,"is_available",return_value=True):
            for key,quote in (("d9","编造的日期"),("d2","编造的原文"),("d1",rows[0]["quote"])):
                with patch.object(llm,"_call_api",return_value=dict(id=key,quote=quote,role="网页发布日期")):
                    self.assertFalse(llm.review_dates("测试",rows)["date"])

    def test_no_date_api_for_old_url_empty_body_or_explicit_label(self):
        self.url="https://fixture.gov.cn/202101/t20210101_123.html"
        with patch.object(self.w.llm,"is_available",return_value=True),patch.object(self.w.llm,"review_dates") as api:
            _,p=self.process("<article>这是一篇没有页面刊发时间标记的历史文章。</article>")
            self.assertEqual(p["status"],"historical_hint")
            _,p=self.process('<meta name="PubDate" content="2026-11-23">',"2026-11-10")
            self.assertEqual(p["failure_kind"],"date_conflict")
            api.assert_not_called()

    def test_budget_keeps_issue_and_procurement_is_not_hard_accepted(self):
        self.w.llm.date_budget = DateRequestBudget(0)
        with patch.object(self.w.llm,"is_available",return_value=True),patch("gov_report.llm_classifier.post_judgment") as api:
            _,p=self.process(f"<h1>{self.title}</h1><article>本通知已于2026-11-22在本网站首次公开，请相关单位按要求执行。</article>")
            api.assert_not_called()
            self.assertIn("上限",p["reason"])
            self.assertEqual((p["status"], p["failure_kind"]), ("detail_failed", "date_budget_exhausted"))
            stats = self.w.llm_statistics()
            self.assertEqual((stats["date_budget_skipped"], stats["success_count"], stats["failure_count"]), (1, 0, 0))
        article=extract_article("<article><h1>专项实验室能力建设项目成交结果公告</h1>现公示本单位采购结果。</article>",self.url)
        cls=classify(article.title,article.text,{},url=self.url,context="栏目:政策文件")
        self.assertEqual(self.w.rule_bucket(article,cls)[0],"ambiguous")

    def test_parallel_limit_is_durable_and_only_applies_to_date_posts(self):
        path = self.root / "task.db"
        llm = self.w.llm
        llm.date_budget = DateRequestBudget(5, TaskState(path))
        def date_review(index):
            return llm.review_dates(str(index), [])
        with patch.object(llm, "is_available", return_value=True), patch("gov_report.llm_classifier.post_judgment",
                side_effect=lambda *a: dict(id="", role="证据不足", quote="")) as post:
            with ThreadPoolExecutor(max_workers=6) as workers:
                results = list(workers.map(date_review, range(37)))
            self.assertEqual(sum(bool(r.get("budget_exhausted")) for r in results), 32)
            llm.date_budget = DateRequestBudget(5, TaskState(path))
            self.assertTrue(date_review(40)["budget_exhausted"])
            self.assertEqual((post.call_count, llm.date_budget.used), (5, 5))
            llm._post("mock", {}, {})
            self.assertEqual((post.call_count, llm.date_budget.used), (6, 5))
            llm.date_budget = DateRequestBudget()
            self.assertTrue(all(date_review(i)["call_succeeded"] for i in range(35)))

    def test_cached_reviews_work_even_at_zero_and_retries_consume_slots(self):
        path = self.root / "dates.jsonl"
        llm = LLMClassifier(path)
        with patch.object(llm, "is_available", return_value=True), patch("gov_report.llm_classifier.post_judgment",
                return_value=dict(id="", role="证据不足", quote="")):
            self.assertTrue(llm.review_dates("cached", [])["call_succeeded"])
        llm = LLMClassifier(path)
        llm.date_budget = DateRequestBudget(0)
        with patch.object(llm, "is_available", return_value=True), patch("gov_report.llm_classifier.post_judgment") as post:
            self.assertTrue(llm.review_dates("cached", [])["from_cache"])
            self.assertTrue(llm.review_dates("other", [])["budget_exhausted"])
            self.assertEqual(llm.date_budget.used, 0)
            post.assert_not_called()
            llm.date_budget = DateRequestBudget(1)
            post.side_effect = ModelCallError("格式不支持", kind="format")
            self.assertTrue(llm.review_dates("other", [])["budget_exhausted"])
            self.assertEqual((post.call_count, llm.date_budget.used), (1, 1))

    def test_real_date_contract_over_mock_http(self):
        import requests
        llm=LLMClassifier(cache_enabled=False)
        quote="本通知于2026-11-24首次公开"
        resp=requests.Response()
        resp.status_code=200; resp.encoding="utf-8"; resp.headers["Content-Type"]="application/json"
        resp._content=json.dumps({"choices":[{"message":{"content":json.dumps(
            {"id":"d1","quote":quote,"role":"网页发布日期"})},"finish_reason":"stop"}]}).encode()
        resp._content_consumed=True
        with patch.object(llm,"is_available",return_value=True),patch("gov_report.llm_classifier.OPENAI_API_STYLE","chat_completions"),patch("gov_report.llm_transport.requests.post",return_value=resp) as post:
            result=llm.review_dates("政策文件",[dict(kind="正文日期线索",date="2026-11-24",quote=quote)])
        self.assertEqual(result["date"],"2026-11-24")
        request=post.call_args.kwargs["json"]
        self.assertEqual(set(request["response_format"]["json_schema"]["schema"]["required"]),{"id","quote","role"})
        self.assertEqual(set(json.loads(request["messages"][1]["content"])),{"标题","日期证据"})

    def test_history_does_not_hide_404_and_remains_unverified(self):
        task=TaskState(self.root/"state.db",{"sources":[{"name":"fixture"}]})
        task.put("source","fixture","state",{"finished":True})
        task.put("candidate","fixture","old",dict(item={"url":"old"},status="historical_hint",reason="仅见期前线索"))
        task.put("candidate","fixture","missing",dict(item={"url":"missing"},status="detail_failed",
                                                     reason="HTTP 404",failure_kind="not_found",http_status=404))
        summary=task.summary()
        self.assertEqual(summary["partial"],1)
        self.assertEqual(summary["counts"]["out_of_range"],0)
        self.assertEqual(summary["counts"]["historical_hint"],1)
        self.assertEqual([i["url"] for i in report_issues({"coverage":summary})],["missing"])
