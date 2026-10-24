from __future__ import annotations

import json
import tempfile
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

from gov_report.cache import ArticleCache
from gov_report.config import load_sources
from gov_report.crawler import GovCrawler
from gov_report.date_utils import resolve_date_range
from gov_report.llm_classifier import LLMClassifier
from gov_report.pagination import DateWindow
from gov_report.parser import Article, LinkItem, extract_links
from gov_report.scope import apply_scope, channel_allowed, core_urls
from main import parse_args


ROOT = Path(__file__).resolve().parent.parent


class CommandLineTests(unittest.TestCase):
    def test_attachments_require_explicit_opt_in_and_scan_controls_are_available(self):
        with patch("sys.argv", ["main.py"]):
            args = parse_args()
            self.assertFalse(args.download_attachments)
            self.assertEqual(args.workers, 3)
            self.assertFalse(args.full_scan)
        with patch("sys.argv", ["main.py", "--download-attachments", "--full-scan", "--no-cache", "--workers", "1"]):
            args = parse_args()
            self.assertTrue(args.download_attachments)
            self.assertTrue(args.full_scan)
            self.assertTrue(args.no_cache)
            self.assertEqual(args.workers, 1)


class ScopeTests(unittest.TestCase):
    def test_inventory_is_preserved_but_all_thirty_sites_have_core_columns(self):
        sources = load_sources(ROOT / "config" / "sources.yaml")
        self.assertEqual(len(sources), 30)
        self.assertEqual(sum(len(source["list_urls"]) for source in sources), 703)
        self.assertLess(sum(len(core_urls(source)) for source in sources), 703)
        self.assertTrue(all(source.get("crawl_scope", {}).get("urls") for source in sources))
        excluded = {"景区收费标准", "来信公示", "招标公告", "中标公告", "拟审查项目公示", "已批准项目公告"}
        for source in sources:
            self.assertFalse(any(source["channel_names"][url] in excluded for url in core_urls(source)))
            personnel = {url for url, name in source["channel_names"].items()
                         if name in {"人事任免", "人事信息", "干部任免", "人事工作信息"}}
            self.assertTrue(personnel.issubset(core_urls(source)))

    def test_scope_does_not_expand_into_a_global_menu_or_lifestyle_column(self):
        source = apply_scope({"base_url": "https://example.gov.cn/", "list_urls": ["https://example.gov.cn/policy/"],
                              "channel_names": {"https://example.gov.cn/policy/": "政策文件"}},
                             {"column_names": ["政策文件", "通知公告"]})
        self.assertTrue(channel_allowed(source, "https://example.gov.cn/policy/notices/", "通知公告"))
        self.assertFalse(channel_allowed(source, "https://example.gov.cn/other/notices/", "通知公告"))
        self.assertFalse(channel_allowed(source, "https://example.gov.cn/policy/life/", "生活资讯"))
        self.assertTrue(channel_allowed(source, "https://example.gov.cn/life/", "生活资讯", full_scan=True))
        self.assertIn(source["base_url"], core_urls(source, full_scan=True))

    def test_unknown_custom_source_keeps_discovery_instead_of_becoming_empty(self):
        source = {"name": "fixture", "base_url": "https://example.gov.cn/", "list_urls": []}
        self.assertEqual(core_urls(apply_scope(source, {"column_names": ["政策文件"]})), [source["base_url"]])


class DateWindowTests(unittest.TestCase):
    start, end = resolve_date_range(start_date="2026-10-20", end_date="2026-10-23")

    def rows(self, *dates):
        html = "".join(f'<li><a href="/art/{day.replace("-", "/")}/art_1_{i}.html">政策通知{i}</a>'
                       f'<span>{day}</span></li>' for i, day in enumerate(dates))
        return extract_links(html, "https://example.gov.cn/policy/")

    def test_stops_only_after_three_ordered_pages_including_two_old_pages(self):
        window = DateWindow(True)
        self.assertFalse(window.observe(self.rows("2026-10-23", "2026-10-22"), self.start))
        self.assertFalse(window.observe(self.rows("2026-10-19", "2026-10-18"), self.start))
        self.assertTrue(window.observe(self.rows("2026-10-17", "2026-10-16"), self.start))

    def test_inclusive_start_boundary_does_not_count_as_an_old_page(self):
        window = DateWindow(True)
        self.assertFalse(window.observe(self.rows("2026-10-21", "2026-10-20"), self.start))
        self.assertEqual(window.old_pages, 0)

    def test_unknown_dates_url_dates_and_one_row_pages_cannot_establish_order(self):
        for rows in ([LinkItem("政策通知", "https://example.gov.cn/202001/article.html")],
                     self.rows("2026-10-19"),
                     [LinkItem("政策通知", "https://example.gov.cn/a", publish_date=self.start - timedelta(days=1))]):
            window = DateWindow(True)
            for _ in range(4):
                self.assertFalse(window.observe(rows, self.start))

    def test_pinned_old_article_does_not_make_current_list_look_exhausted(self):
        rows = self.rows("2026-10-19", "2026-10-23", "2026-10-22")
        rows[0].pinned = True
        window = DateWindow(True)
        self.assertFalse(window.observe(rows, self.start))
        self.assertEqual(window.old_pages, 0)
        self.assertFalse(window.disabled)

    def test_unsorted_pages_disable_date_stopping_for_the_whole_chain(self):
        for first, second in ((self.rows("2026-10-18", "2026-10-19"), self.rows("2026-10-17", "2026-10-16")),
                              (self.rows("2026-10-19", "2026-10-18"), self.rows("2026-10-23", "2026-10-22"))):
            window = DateWindow(True)
            window.observe(first, self.start)
            self.assertFalse(window.observe(second, self.start))
            self.assertTrue(window.disabled)

    def test_parser_does_not_treat_a_date_in_the_title_or_url_as_a_list_date(self):
        html = '<li><a href="/art/2020/1/1/art_1_1.html">关于2020年1月1日文件的政策解读</a></li>'
        self.assertFalse(extract_links(html, "https://example.gov.cn/")[0].date_reliable)
        html = '<li class="pinned"><a href="/a.html">人事任免</a><time>2026-10-23</time></li>'
        row = extract_links(html, "https://example.gov.cn/")[0]
        self.assertTrue(row.pinned)
        self.assertTrue(row.date_reliable)

    def test_list_date_takes_priority_over_a_date_mentioned_in_the_title(self):
        html = '<li><a href="/a.html">关于2020年1月1日文件的政策解读</a><span>2026-10-23</span></li>'
        item = extract_links(html, "https://example.gov.cn/")[0]
        self.assertEqual(item.date_text, "2026-10-23")
        self.assertTrue(item.date_reliable)

    def test_date_inside_anchor_is_not_part_of_title_and_is_reliable(self):
        html = '<li><a href="/a.html">人事任免通知<span>2026-10-23</span></a></li>'
        item = extract_links(html, "https://example.gov.cn/")[0]
        self.assertEqual(item.title, "人事任免通知")
        self.assertEqual(item.date_text, "2026-10-23")
        self.assertTrue(item.date_reliable)


class CacheTests(unittest.TestCase):
    def test_reuses_older_articles_but_revalidates_recent_undated_and_expired_ones(self):
        now = datetime(2026, 10, 24, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            cache = ArticleCache(Path(folder))
            for name, date, age, expected in (("older", now - timedelta(days=4), 3600, True),
                                               ("recent", now - timedelta(hours=12), 3600, False),
                                               ("undated", None, 3600, False),
                                               ("expired", now - timedelta(days=30), 8 * 86400, False)):
                article = Article(name, "https://example.gov.cn/" + name, date, "正文" * 80, [])
                cache.put(name, article, now=now.timestamp() - age)
                cached = cache.get(name, now=now.timestamp())
                self.assertEqual(cached is not None, expected)
                if expected:
                    self.assertEqual(cached.text, article.text)

    def test_cache_reapplies_date_and_classification_in_a_different_report_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = {"name": "fixture", "base_url": "https://example.gov.cn/"}
            article = Article("人事任免通知", source["base_url"] + "article.html",
                              datetime(2026, 1, 5, tzinfo=timezone.utc), "任命相关人员。" * 40, [])
            for name in ("range-one", "range-two"):
                crawler = GovCrawler([source], {}, root / name, use_llm=False)
                crawler.client = Mock()
                crawler.client.fetch_text.return_value = (
                    '<meta name="PubDate" content="2026-01-05"><h1>人事任免通知</h1><div class="TRS_Editor">' + article.text + '</div>',
                    article.url)
                crawler.log = Mock()
                loaded, cached = crawler.load_article(article.url, article.title, "fixture")
                self.assertEqual(cached, name == "range-two")
                self.assertEqual(crawler.client.fetch_text.call_count, int(name == "range-one"))
            start, end = resolve_date_range(start_date="2026-02-01", end_date="2026-02-07")
            crawler.decide_with_optional_llm = Mock()
            record, _ = crawler.process_candidate(source, LinkItem(article.title, article.url), start, end)
            self.assertIsNone(record)
            crawler.decide_with_optional_llm.assert_not_called()

    def test_failed_fetch_is_never_saved(self):
        with tempfile.TemporaryDirectory() as folder:
            crawler = GovCrawler([], {}, Path(folder) / "report", use_llm=False)
            crawler.client = Mock()
            crawler.client.fetch_text.side_effect = RuntimeError("offline fixture")
            with self.assertRaises(RuntimeError):
                crawler.load_article("https://example.gov.cn/a.html", "政策通知", "fixture")
            self.assertIsNone(crawler.cache.get("parser-v2|//example.gov.cn/a.html"))

    def test_model_and_prompt_changes_invalidate_judgment_cache(self):
        classifier = LLMClassifier()
        key = classifier._cache_key({"url": "https://example.gov.cn/a"}, "fixture")
        for field in ("OPENAI_MODEL", "OPENAI_BASE_URL", "SYSTEM_PROMPT"):
            with patch("gov_report.llm_classifier." + field, "changed"):
                self.assertNotEqual(key, classifier._cache_key({"url": "https://example.gov.cn/a"}, "fixture"))


class CrawlFlowTests(unittest.TestCase):
    def crawl_fixture(self, folder, *, full_scan=False):
        root = "https://example.gov.cn/"
        source = {"name": "fixture", "base_url": root, "list_urls": [root + "policy/", root + "life/"],
                  "channel_names": {root + "policy/": "政策文件", root + "life/": "生活资讯"},
                  "crawl_scope": {"urls": [root + "policy/"], "column_names": ["政策文件"], "date_stop": True}}
        pages = {root: '<a href="/policy/">政策文件</a>', root + "life/": "生活资讯"}
        for index in range(1, 11):
            url = root + "policy/" if index == 1 else root + f"policy/page{index}"
            days = [23, 22] if index == 1 else [21 - index * 2, 20 - index * 2]
            rows = []
            for position, day in enumerate(days):
                day = max(1, day)
                article = root + f"art/2026/10/{day}/art_{index}_{position}.html"
                rows.append(f'<li><a href="{article}">人事任免通知{index}-{position}</a><span>2026-10-{day:02}</span></li>')
                pages[article] = f'<meta name="PubDate" content="2026-10-{day:02}"><h1>人事任免通知{index}-{position}</h1><div class="TRS_Editor">人事任免正文。</div>'
            pages[url] = "".join(rows) + (f'<a rel="next" href="/policy/page{index + 1}">下一页</a>' if index < 10 else "")
        crawler = GovCrawler([source], {}, folder, use_llm=False, use_cache=False, full_scan=full_scan, sleep=0)
        crawler.client = Mock()
        crawler.client.fetch_text.side_effect = lambda url: (pages[url], url)
        crawler.log = Mock()
        start, end = resolve_date_range(start_date="2026-10-20", end_date="2026-10-23")
        records = crawler.crawl_source(source, start, end)
        return records, [call.args[0] for call in crawler.client.fetch_text.call_args_list]

    def test_core_date_scan_matches_full_scan_without_fetching_lifestyle_or_old_pages(self):
        with tempfile.TemporaryDirectory() as folder:
            core, core_calls = self.crawl_fixture(folder)
            full, full_calls = self.crawl_fixture(folder, full_scan=True)
        self.assertEqual({row["url"] for row in core}, {row["url"] for row in full})
        self.assertEqual(len(core), 2)
        self.assertEqual(len(core_calls), 5)
        self.assertEqual(len(full_calls), 14)
        self.assertFalse(any("life/" in url or "page4" in url for url in core_calls))
        # A detail is processed before the next list page, rather than waiting for traversal.
        self.assertIn("/art/", core_calls[1])

    def test_url_date_alone_does_not_skip_a_republished_article(self):
        with tempfile.TemporaryDirectory() as folder:
            crawler = GovCrawler([], {}, folder, use_llm=False, use_cache=False)
            crawler.client = Mock()
            url = "https://example.gov.cn/art/2020/1/1/art_1_1.html"
            crawler.client.fetch_text.return_value = ('<meta name="PubDate" content="2026-10-23"><h1>人事任免通知</h1><article>任免正文</article>', url)
            start, end = resolve_date_range(start_date="2026-10-20", end_date="2026-10-23")
            item = extract_links(f'<a href="{url}">人事任免通知</a>', "https://example.gov.cn/")[0]
            record, _ = crawler.process_candidate({"name": "fixture"}, item, start, end)
            self.assertIsNotNone(record)

    def test_different_sites_run_concurrently_and_keep_deterministic_result_order(self):
        lock = threading.Lock()
        barrier = threading.Barrier(3)
        active = maximum = 0

        def fake_crawl(worker, source, start, end):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            barrier.wait(timeout=5)
            with lock:
                active -= 1
            return [{"url": source["base_url"], "title": source["name"], "source_name": source["name"]}]

        sources = [{"name": str(index), "base_url": f"https://site{index}.example.gov.cn/"} for index in range(3)]
        with tempfile.TemporaryDirectory() as folder, patch.object(GovCrawler, "crawl_source", fake_crawl):
            crawler = GovCrawler(sources, {}, folder, use_llm=False, use_cache=False)
            records = crawler.crawl(None, None)
        self.assertEqual(maximum, 3)
        self.assertEqual([row["title"] for row in records], ["0", "1", "2"])

    def test_two_sources_on_the_same_host_are_not_fetched_concurrently(self):
        lock = threading.Lock()
        active = maximum = 0

        def fake_crawl(worker, source, start, end):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.02)
            with lock:
                active -= 1
            return []

        sources = [{"name": str(index), "base_url": "https://example.gov.cn/"} for index in range(2)]
        with tempfile.TemporaryDirectory() as folder, patch.object(GovCrawler, "crawl_source", fake_crawl):
            crawler = GovCrawler(sources, {}, folder, use_llm=False, use_cache=False)
            crawler.crawl(None, None)
        self.assertEqual(maximum, 1)

    def test_collecting_records_never_downloads_attachments(self):
        with tempfile.TemporaryDirectory() as folder:
            crawler = GovCrawler([], {}, folder, use_llm=False, use_cache=False, download_attachments=True)
            crawler.client = Mock()
            article = Article("人事任免通知", "https://example.gov.cn/a", None, "任免正文",
                              [{"name": "名单", "url": "https://example.gov.cn/a.pdf"}])
            record = crawler.article_to_record({"name": "fixture"}, article, None, {"categories": ["人事任免"]})
            crawler.client.download.assert_not_called()
            self.assertEqual(record["attachments"][0]["local_path"], "")
            crawler.client.download.return_value = Path(folder) / "download.pdf"
            crawler.download_record_attachments([record])
            crawler.client.download.assert_called_once()
            self.assertEqual(record["attachments"][0]["local_path"], "download.pdf")
            self.assertTrue((Path(folder) / "attachment_downloads.json").is_file())

    def test_failed_attachment_does_not_abort_the_post_pdf_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            crawler = GovCrawler([], {}, folder, use_llm=False, use_cache=False, download_attachments=True)
            crawler.client = Mock()
            crawler.client.download.side_effect = OSError("fixture disk failure")
            records = [{"title": "通知", "url": "https://example.gov.cn/a", "source_name": "fixture",
                        "attachments": [{"name": "附件", "url": "https://example.gov.cn/a.pdf"}]}]
            crawler.download_record_attachments(records)
            self.assertEqual(crawler.metrics.snapshot()["attachment"]["errors"], 1)
            self.assertEqual(records[0]["attachments"][0]["local_path"], "")

    def test_one_site_failure_does_not_abort_other_sites(self):
        def fake_crawl(worker, source, start, end):
            if source["name"] == "bad":
                raise RuntimeError("fixture failure")
            return [{"url": source["base_url"], "source_name": source["name"], "title": "政策通知"}]

        sources = [{"name": name, "base_url": f"https://{name}.example.gov.cn/"} for name in ("bad", "good")]
        events = []
        with tempfile.TemporaryDirectory() as folder, patch.object(GovCrawler, "crawl_source", fake_crawl):
            crawler = GovCrawler(sources, {}, folder, use_llm=False, use_cache=False,
                                 progress_callback=events.append)
            records = crawler.crawl(None, None)
        self.assertEqual([record["source_name"] for record in records], ["good"])
        self.assertEqual(sum(event["event"] == "source_finished" for event in events), 2)
        self.assertTrue(any(event["event"] == "error" for event in events))


if __name__ == "__main__":
    unittest.main()
