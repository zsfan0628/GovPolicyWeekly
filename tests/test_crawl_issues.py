import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
from bs4 import BeautifulSoup

from gov_report.config import load_sources
from gov_report.crawl_issues import NonHtmlContent, failure_details, report_issues
from gov_report.crawler import GovCrawler
from gov_report.date_utils import resolve_date_range
from gov_report.http import HttpClient
from gov_report.parser import LinkItem, extract_attachments, discover_channel_urls
from gov_report.scope import core_urls, channel_allowed
from gov_report.task_state import TaskState


class CrawlIssueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.source = dict(name='测试站点', base_url='https://example.gov.cn/',
                           list_urls=['https://example.gov.cn/policy/'])
        self.task = TaskState(self.root / 'task.sqlite3', dict(sources=[self.source]))
        self.crawler = GovCrawler([self.source], {}, self.root, use_cache=False, use_llm=False,
                                  sleep=0, max_workers=1, task_state=self.task)
        self.crawler.client = Mock()
        self.crawler.log = Mock()
        self.start, self.end = resolve_date_range(start_date='2026-11-07', end_date='2026-11-14')

    def tearDown(self):
        self.temp.cleanup()

    def test_attachments_are_skipped_without_fetch_or_error_and_remain_links(self):
        urls = ['https://example.gov.cn/a.OFD',
                'https://example.gov.cn/truecms/attachmentController/download.do?id=123&type=ht',
                'https://example.gov.cn/zxfile/reader?file=https%3A%2F%2Fexample.gov.cn%2Fa.pdf']
        html = ''.join(f'<a href="{url}">政策文件</a>' for url in urls)
        self.assertEqual(discover_channel_urls(html, self.source['base_url']), [])
        self.assertEqual(len(extract_attachments(BeautifulSoup(html, 'html.parser'), self.source['base_url'])), 3)
        for url in urls:
            item = LinkItem('政策文件', url)
            self.assertFalse(self.crawler.should_fetch_candidate(item))
            self.crawler.process_candidate(self.source, item, self.start, self.end)
        self.crawler.client.fetch_text.assert_not_called()
        self.task.put('source', self.source['name'], 'state', dict(finished=True))
        summary = self.task.summary()
        self.assertEqual(summary['counts']['skipped_attachment'], 3)
        self.assertEqual(summary['complete'], 1)
        self.assertEqual(report_issues({'coverage': summary}), [])

    def test_binary_response_is_not_retried_in_browser_or_alternate_scheme(self):
        client = HttpClient(sleep=0, browser_fallback=True)
        with patch.object(client, '_fetch_text_requests', side_effect=NonHtmlContent('document')) as fetch, \
                patch.object(client, '_fetch_text_browser') as browser:
            with self.assertRaises(NonHtmlContent):
                client.fetch_text('https://example.gov.cn/document?id=123')
            fetch.assert_called_once()
            browser.assert_not_called()

    def test_unrecognized_binary_candidate_counts_as_skip_not_failure(self):
        self.crawler.client.fetch_text.side_effect = NonHtmlContent('document')
        self.crawler.process_candidate(self.source, LinkItem('政策文件', 'https://example.gov.cn/content/123'), self.start, self.end)
        self.assertEqual(self.task.summary()['counts']['skipped_attachment'], 1)
        self.assertEqual(self.crawler.metrics.snapshot()['detail']['errors'], 0)

    def test_failed_page_reason_is_safe_and_successful_retry_removes_issue(self):
        error = RuntimeError('404 Client Error: Not Found; private-response-value')
        self.crawler.client.fetch_text.side_effect = error
        self.crawler.crawl(self.start, self.end)
        issues = report_issues({'coverage': self.task.summary()})
        self.assertEqual(len(issues), 2)  # homepage and configured list
        self.assertEqual(issues[0]['http_status'], 404)
        self.assertNotIn('private-response-value', json.dumps(issues))
        for _, url, _ in self.task.rows('page'):
            self.task.put('page', self.source['name'], url, {'status': 'complete'})
        self.assertEqual(report_issues({'coverage': self.task.summary()}), [])

    def test_detail_and_list_failures_are_deduplicated_but_not_model_errors(self):
        page = dict(url='https://example.gov.cn/404', status='failed', reason='404')
        context = {'coverage': {'sources': [dict(name='site', details=[page, page], issues=[
            dict(url='https://example.gov.cn/a', status='llm_failed'),
            dict(url='https://example.gov.cn/b', status='detail_failed')])]}}
        self.assertEqual(len(report_issues(context)), 2)

    def test_error_classification_does_not_leak_response_or_misread_url_digits(self):
        result = failure_details(RuntimeError('412 Client Error; Timeout 20000ms; net::ERR_BLOCKED_BY_CLIENT; private-value'))
        self.assertIn('412', result['reason'])
        self.assertIn('超时', result['reason'])
        self.assertIn('浏览器阻止', result['reason'])
        self.assertNotIn('private-value', result['reason'])
        self.assertIsNone(failure_details(RuntimeError('https://example.gov.cn/404/page'))['http_status'])

    def test_hlj_entry_overrides_preserve_channels_and_exclude_old_shells(self):
        source = next(x for x in load_sources(Path(__file__).resolve().parents[1] / 'config/sources.yaml')
                      if x['name'] == '黑龙江省生态环境厅')
        urls = core_urls(source)
        for old, new in source['entry_overrides'].items():
            if old in source['crawl_scope']['urls']:
                self.assertIn(new, urls)
                self.assertNotIn(old, urls)
                self.assertTrue(channel_allowed(source, new, ''))
            self.assertFalse(channel_allowed(source, old, source['channel_names'][old]))
        self.assertEqual(len(urls), len(set(urls)))
        self.assertTrue(channel_allowed(source, 'http://sthj.hlj.gov.cn/common/search/abc?page=1', '干部任免'))

    def test_public_channel_directory_keeps_parent_and_child_pagination_routes(self):
        response = requests.Response()
        response.url = 'http://sthj.hlj.gov.cn/common/getChannelList?channelCode=c111978&websiteCodeName=sthj'
        response._content = json.dumps({'results': {'channelId': 'parent-id', 'channelName': '人事信息',
            'children': [{'channelId': 'child-id', 'channelName': '干部任免', 'isChildren': True,
                          'channelCode': 'c123'}]}}).encode()
        html = HttpClient.render_channel_response(response)
        self.assertIn('/common/search/parent-id', html)
        self.assertIn('/common/search/child-id', html)
        self.assertIn('channelCode=c123', html)
