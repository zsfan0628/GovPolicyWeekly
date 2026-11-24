import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from gov_report.crawler import GovCrawler, dedupe_records, mark_same_text_sources
from gov_report.date_utils import resolve_date_range
from gov_report.parser import LinkItem, extract_article
from gov_report.task_state import TaskState
from scripts.check_review_sample import compare


class RetrievalQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = 'https://example.gov.cn/'
        self.list_url = self.base + 'policy/'
        self.url = self.base + 'detail?id=3'
        self.source = dict(name='fixture', base_url=self.base, list_urls=[self.list_url],
                           channel_names={self.list_url: '政策文件'}, crawl_scope={'urls': [self.list_url], 'column_names':['政策文件']})
        self.start, self.end = resolve_date_range(start_date='2026-10-20', end_date='2026-10-23')

    def worker(self, sub='task'):
        task = TaskState(self.root / sub, {'sources':[self.source]})
        w = GovCrawler([self.source], {}, self.root, task_state=task, use_cache=False, use_llm=False)
        w.client = Mock()
        w.log = Mock()
        return w, task

    def test_list_outcomes(self):
        for i, (html, expected, label) in enumerate([
            ('<nav><a href="/info/">政策文件</a></nav>', 'empty', '需核查'),
            ('<div class="list-empty">暂无数据</div>', 'complete', '暂无记录'),
            ('<div>页面加载中</div>', 'empty', '需核查'),
            ('<li><a href="/detail?id=3">关于开展职务任免的通知</a><span>2021-01-03</span></li>', 'complete', '本期之外'),
        ]):
            w, task = self.worker(str(i))
            w.client.fetch_text.return_value = (html, self.list_url)
            w.crawl(self.start, self.end)
            p = task.get('page', 'fixture', self.list_url)
            self.assertEqual(p['status'], expected)
            self.assertIn(label, p['outcome'])
            self.assertEqual(w.client.fetch_text.call_count, 1)

    def test_reliable_list_date_beats_update_date_and_conflict_is_retained(self):
        w, _ = self.worker()
        item = LinkItem('关于职务任免的通知', self.url, publish_date=self.start, date_reliable=True)
        a = extract_article('<article><h1>职务任免通知</h1>更新时间：2020-01-01 经研究决定，任命张某。</article>', self.url)
        w.load_article = Mock(return_value=(a, False))
        w.decide_with_optional_llm = Mock(return_value={'include': True, 'cls': {'categories':['人事任免']}})
        record,_ = w.process_candidate(self.source, item, self.start, self.end)
        self.assertEqual(record['date_source'], '列表标注日期')
        self.assertTrue(record['date_conflict'])
        self.assertEqual(record['publish_date'], '2026-10-20')

    def test_date_ranking_and_url_only_review(self):
        a = extract_article('<article>成文日期：2020-01-01 发布日期：2026-10-20</article>', self.url)
        self.assertEqual(a.date_source, '发布日期')
        self.assertEqual(a.publish_date.day, 20)
        w, task = self.worker()
        item = LinkItem('关于职务任免的通知', self.base+'2026/10/22/art_1_2.html')
        w.client.fetch_text.return_value = ('<article>任职免职决定正文。</article>',item.url)
        w.process_candidate(self.source, item, self.start, self.end)
        self.assertEqual(task.get('candidate','fixture',item.url)['status'], 'detail_failed')

    def test_empty_body_is_not_an_error_for_a_reliably_dated_old_notice(self):
        for i,(published,list_date,expected) in enumerate([
            ("2026-01-09",None,"out_of_range"),
            ("2026-10-21",None,"detail_failed"),
            ("2026-01-09",self.start,"detail_failed"),
        ]):
            w, task = self.worker(str(i))
            w.progress = Mock()
            a = extract_article(f'<meta name="PubDate" content="{published}">',self.url)
            a.text = ""
            w.load_article = Mock(return_value=(a,False))
            item = LinkItem("招聘公告",self.url,publish_date=list_date,date_reliable=list_date is not None)
            w.process_candidate(self.source,item,self.start,self.end)
            saved = task.get("candidate","fixture",self.url)
            self.assertEqual(saved["status"],expected)
            if expected=="out_of_range":
                w.progress.assert_not_called()
            else:
                self.assertEqual(saved["failure_kind"],"date_conflict" if list_date else "content_unparsed")
                w.progress.assert_called_once_with("error",source="fixture",kind="detail",url=self.url,failure_kind=saved["failure_kind"])

    def test_annual_website_report_navigation_is_not_an_article(self):
        w,_ = self.worker()
        self.assertFalse(w.should_fetch_candidate(LinkItem("政府网站工作年度报表",self.url,publish_date=self.start,context="政策")))
        self.assertTrue(w.should_fetch_candidate(LinkItem("关于报送政府网站工作年度报表的通知",self.url,publish_date=self.start,context="政策")))

    def test_stronger_evidence_clears_a_previously_reported_issue(self):
        w, task = self.worker()
        w.progress = Mock()
        item = LinkItem("公告",self.base+"2026/10/22/art_1_2.html")
        w.client.fetch_text.return_value = ("<article>任命通知正文。</article>",item.url)
        w.process_candidate(self.source,item,self.start,self.end)
        self.assertEqual(task.get("candidate","fixture",item.url)["status"],"detail_failed")
        item.publish_date = self.start.replace(year=2025)
        item.date_reliable = True
        w.process_candidate(self.source,item,self.start,self.end,reconsider=True)
        saved = task.get("candidate","fixture",item.url)
        self.assertEqual(saved["status"],"out_of_range")
        self.assertNotIn("failure_kind",saved)
        w.progress.assert_any_call("issue_resolved",source="fixture",url=item.url,kind="candidate")

    def test_reconsidering_columns_does_not_refetch_or_keep_stale_decision(self):
        other = self.base + 'news/'
        for i, urls in enumerate(([self.list_url, other], [other, self.list_url])):
            w, task = self.worker(str(i))
            s = dict(self.source, crawl_scope={'urls':urls}, channel_names={other:'动态', self.list_url:'政策文件'})
            listing = '<li><a href="/detail?id=3">关于开展企业申报的通知</a><span>2026-10-20</span></li>'
            detail = '<article><h1>关于开展企业申报的通知</h1>发布日期：2026-10-20 具体要求见附件。</article>'
            w.client.fetch_text.side_effect = lambda url: (detail if url==self.url else listing, url)
            w.crawl_source(s, self.start, self.end)
            saved = task.get('candidate','fixture',self.url)
            self.assertIn('栏目:政策文件',saved['item']['context'])
            self.assertIn('栏目:动态',saved['item']['context'])
            self.assertEqual(sum(c.args==(self.url,) for c in w.client.fetch_text.call_args_list),1)
            outcome = (saved['status'], saved['column'])
            if i: self.assertEqual(first, outcome)
            else: first = outcome

    def test_no_title_only_dedup_and_quality_sample(self):
        r = dict(title='关于企业申报的通知', source_name='某局', publish_date='2026-10-20', content_hash='one', url=self.url)
        other = dict(r, url=self.url+'4', content_hash='two')
        self.assertEqual(len(dedupe_records([r, other, dict(r)])), 2)
        copy = dict(r, source_name='另一部门', url=self.url+'5')
        mark_same_text_sources([r, other, copy])
        self.assertEqual(r["same_text_sources"], ["另一部门"])
        self.assertNotIn("same_text_sources", other)
        review = compare([r], [{'url':other['url'], 'decision':'include'}, {'url':r['url'], 'decision':'exclude'}])
        self.assertEqual(review['missed'], [other['url']])
        self.assertEqual(review['unexpected'], [r['url']])

    def test_fresh_check_opens_candidate_despite_old_list_date(self):
        w, task = self.worker()
        w.verify_dates = True
        old, _ = resolve_date_range(start_date='2020-10-20', end_date='2020-10-23')
        item = LinkItem('职务任免通知', self.url, publish_date=old, date_reliable=True)
        w.client.fetch_text.return_value = ('<meta name="PubDate" content="2026-10-20"><article>'
                                            '<h1>职务任免通知</h1>经研究决定，任命张某为主任。</article>', self.url)
        w.process_candidate(self.source,item,self.start,self.end)
        w.client.fetch_text.assert_called_once_with(self.url)
        record = task.records()[0]
        self.assertTrue(record['date_conflict'])
        self.assertEqual(record['date_source'], '发布元数据')
