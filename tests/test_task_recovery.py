from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from gov_report.crawler import GovCrawler
from gov_report.date_utils import resolve_date_range
from gov_report.model_probe import run_probe
from gov_report.parser import Article, LinkItem
from gov_report.task_state import TaskState, task_lock


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.base = "https://example.gov.cn/"
        self.source = dict(name="fixture", base_url=self.base, list_urls=[self.base + "policy/"],
                           crawl_scope={"urls": [self.base + "policy/"], "column_names": ["政策文件"]})
        self.start, self.end = resolve_date_range(start_date="2026-10-20", end_date="2026-10-23")
        self.metadata = dict(sources=[self.source], start_date="2026-10-20", end_date="2026-10-23")
        self.task = TaskState(self.root / "task.sqlite3", self.metadata)
        self.url = self.base + "art/2026/10/23/art_1_1.html"
        self.html = f'<li><a href="{self.url}">人事任免通知</a><span>2026-10-23</span></li>'
        self.article = '<meta name="PubDate" content="2026-10-23"><h1>人事任免通知</h1><article>人事任免正文。</article>'

    def tearDown(self):
        self.temp.cleanup()

    def crawler(self):
        crawler = GovCrawler([self.source], {}, self.root, use_llm=False, use_cache=False,
                             sleep=0, max_workers=1, task_state=self.task)
        crawler.client = Mock()
        crawler.log = Mock()
        return crawler

    def test_failed_detail_retry_reuses_list_and_keeps_successful_source(self):
        crawler = self.crawler()
        crawler.client.fetch_text.side_effect = [(self.html, self.base + "policy/"), OSError("offline")]
        self.assertEqual(crawler.crawl(self.start, self.end), [])
        self.assertEqual(self.task.summary()["partial"], 1)
        self.assertEqual(self.task.summary()["counts"]["detail_failed"], 1)
        self.task = TaskState(self.task.path, self.metadata)
        retry = self.crawler()
        retry.client.fetch_text.return_value = (self.article, self.url)
        self.assertEqual(len(retry.crawl(self.start, self.end)), 1)
        retry.client.fetch_text.assert_called_once_with(self.url)
        self.assertEqual(self.task.summary()["complete"], 1)
        again = self.crawler()
        self.assertEqual(len(again.crawl(self.start, self.end)), 1)
        again.client.fetch_text.assert_not_called()

    def test_failed_list_is_not_zero_result_success_and_is_retried(self):
        crawler = self.crawler()
        crawler.client.fetch_text.side_effect = OSError("offline")
        crawler.crawl(self.start, self.end)
        self.assertEqual(self.task.summary()["failed"], 1)
        retry = self.crawler()
        retry.client.fetch_text.side_effect = [(self.html, self.base + "policy/"), (self.article, self.url)]
        self.assertEqual(len(retry.crawl(self.start, self.end)), 1)
        self.assertEqual(self.task.summary()["complete"], 1)

    def test_empty_html_is_a_warning_not_a_complete_site(self):
        crawler = self.crawler()
        crawler.client.fetch_text.return_value = ("<html>access denied</html>", self.base + "policy/")
        crawler.crawl(self.start, self.end)
        self.assertEqual(self.task.summary()["failed"], 1)
        self.assertEqual(self.task.summary()["sources"][0]["details"][0]["status"], "empty")

    def test_unknown_date_is_incomplete_and_retry_fetches_the_article_again(self):
        crawler = self.crawler()
        crawler.load_article = Mock(return_value=(Article("通知", self.url, None, "测试正文", []), False))
        crawler.process_candidate(self.source, LinkItem("通知", self.url), self.start, self.end)
        self.assertEqual(self.task.summary()["counts"]["detail_failed"], 1)
        retry = self.crawler()
        retry.client.fetch_text.return_value = (self.article, self.url)
        record, _ = retry.process_candidate(self.source, LinkItem("通知", self.url), self.start, self.end)
        self.assertIsNotNone(record)
        retry.client.fetch_text.assert_called_once_with(self.url)

    def test_interruption_after_article_fetch_uses_durable_snapshot(self):
        crawler = self.crawler()
        crawler.client.fetch_text.side_effect = [(self.html, self.base + "policy/"), (self.article, self.url)]
        crawler.decide_with_optional_llm = Mock(side_effect=KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            crawler.crawl(self.start, self.end)
        self.assertEqual(self.task.summary()["pending"], 1)
        retry = self.crawler()
        self.assertEqual(len(retry.crawl(self.start, self.end)), 1)
        retry.client.fetch_text.assert_not_called()

    def test_model_only_retry_does_not_fetch_pages_and_preserves_records(self):
        crawler = self.crawler()
        crawler.load_article = Mock(return_value=(Article("申报通知", self.url, self.start, "测试正文", []), False))
        crawler.decide_with_optional_llm = Mock(return_value={"include": False, "status": "llm_failed", "reason": "调用失败"})
        crawler.process_candidate(self.source, LinkItem("申报通知", self.url), self.start, self.end)
        self.task.put("candidate", "fixture", "old", {"status": "included", "record": {"title": "已收录", "url": "old"}})
        retry = self.crawler()
        retry.llm = Mock()
        retry.decide_with_optional_llm = Mock(return_value={"include": True, "cls": {"categories": ["政策文件"]}})
        records = retry.retry_model_failures(self.start, self.end)
        self.assertEqual(len(records), 2)
        retry.client.fetch_text.assert_not_called()
        self.assertEqual(retry.decide_with_optional_llm.call_count, 1)
        self.assertEqual(self.task.summary()["counts"]["llm_failed"], 0)

    def test_changed_scope_cannot_reuse_task(self):
        with self.assertRaisesRegex(ValueError, "任务日期"):
            TaskState(self.task.path, {**self.metadata, "start_date": "2026-01-01"})
        self.assertEqual(self.task.get("meta", "", "task"), self.metadata)

    def test_summary_does_not_expose_page_bodies(self):
        self.task.put("page_html", "fixture", "url", {"html": "large body"})
        self.assertNotIn("large body", str(self.task.summary()))

    def test_task_lock_rejects_concurrent_resume_and_releases_after_failure(self):
        with self.assertRaisesRegex(RuntimeError, "interrupt"):
            with task_lock(self.task.path):
                with self.assertRaisesRegex(ValueError, "另一个进程"):
                    with task_lock(self.task.path):
                        self.fail("Concurrent acquisition must fail")
                raise RuntimeError("interrupt")
        with task_lock(self.task.path):
            pass


class ProbeTests(unittest.TestCase):
    @patch("gov_report.llm_classifier.LLMClassifier")
    def test_real_classification_path_bypasses_cache_and_accepts_semantic_rejection(self, classifier):
        classifier.return_value.classify_article.return_value = {"call_succeeded": True, "include": False, "model": "fixture"}
        result = run_probe()
        self.assertTrue(result["ok"])
        classifier.assert_called_once_with(cache_enabled=False)
        self.assertIn("虚构", classifier.return_value.classify_article.call_args.args[0]["text"])

    @patch("gov_report.llm_classifier.LLMClassifier")
    def test_transport_failure_is_not_a_pass(self, classifier):
        classifier.return_value.classify_article.return_value = {"call_succeeded": False, "reason": "认证失败"}
        self.assertEqual(run_probe()["error"], "认证失败")


if __name__ == "__main__":
    unittest.main()
