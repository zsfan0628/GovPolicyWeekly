import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pypdf import PdfReader

from gov_report.date_utils import resolve_date_range
from gov_report.pdf_report import clean_excerpt, grouped_records, source_link
from gov_report.report import export_all, export_pdf_direct
from scripts.prepare_github_source import ROOT, collect_paths


class PdfReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.start, self.end = resolve_date_range(start_date='2026-10-17', end_date='2026-10-23')

    def tearDown(self):
        self.temp.cleanup()

    def record(self, **changes):
        return dict(dict(title='关于化工企业申报的通知', source_name='测试发布单位', publish_date='2026-10-23',
                         category='政策文件', summary='符合要求的企业可按通知要求申报。',
                         url='https://example.gov.cn/article?a=1&b=2', decision_source='规则硬通过',
                         attachments=[{'name': '附件名单', 'url': 'https://example.gov.cn/list.pdf'}]), **changes)

    def export(self, records, context=None):
        p = export_pdf_direct(records, self.root / 'report.pdf', self.start, self.end, {}, context)
        return PdfReader(p)

    def test_fonts_links_page_counts_and_original_data_preserved(self):
        records = [self.record(), self.record(title='关于职务任免的通知', category='人事任免、政策文件',
                                              url='https://example.gov.cn/personnel')]
        original = repr(records)
        reader = self.export(records)
        urls, internal = [], []
        for i, page in enumerate(reader.pages, 1):
            self.assertIn(f'第 {i} / {len(reader.pages)} 页', page.extract_text())
            for ref in page.get('/Annots', []):
                a = ref.get_object()
                if a.get('/A', {}).get('/URI'):
                    urls.append(a['/A']['/URI'])
                if '/Dest' in a:
                    internal.append(a['/Dest'])
            for f in page['/Resources']['/Font'].values():
                f = f.get_object()
                name = str(f['/BaseFont'])
                self.assertNotIn('STSong', name)
                if 'GovSans' in name or 'SourceHan' in name:
                    self.assertIn('/FontFile2', f['/FontDescriptor'])
        for record in records:
            self.assertGreaterEqual(urls.count(record['url']), 3)
        self.assertEqual(len(internal), 4)
        self.assertEqual(repr(records), original)
        self.assertEqual([len(x[2]) for x in grouped_records(records)], [1, 1])

    def test_empty_and_partial_reports_do_not_claim_complete_collection(self):
        r = self.export([])
        text = ''.join(p.extract_text() for p in r.pages)
        self.assertIn('暂无收录', text)
        self.assertIn('未提供逐站完成记录', text)
        r = self.export([], {'coverage': {'partial': 1, 'counts': {'llm_failed': 2}, 'sources': [
            {'name': '测试站点', 'status': 'partial', 'label': '部分失败', 'issues': [
                {'title': '待复判文章', 'url': 'https://example.gov.cn/failure', 'status': 'llm_failed', 'reason': '认证失败'}]}]}})
        text = ''.join(p.extract_text() for p in r.pages)
        self.assertIn('2 条', text)
        self.assertIn('认证失败', text)

    def test_long_titles_summaries_and_attachments_split_without_losing_tail(self):
        r = self.export([self.record(title='很长的通知标题' * 180 + '标题结尾',
                                     summary='这是用于检查跨页的完整正文内容。' * 650 + '正文结尾标记',
                                     attachments=[{'name': '附件' + str(i), 'url': f'https://example.gov.cn/{i}.pdf'} for i in range(65)])])
        text = ''.join(p.extract_text().replace('\n', '') for p in r.pages)
        self.assertIn('标题结尾', text)
        self.assertIn('正文结尾标记', text)
        self.assertIn('附件64', text)
        self.assertGreater(len(r.pages), 4)

    def test_unsafe_urls_are_not_links_and_markup_is_escaped(self):
        embedded_credentials = 'https://' + 'user:pass@' + 'example.com'
        for url in ('javascript:alert(1)', 'file:///tmp/private', '//example.com', embedded_credentials):
            self.assertNotIn('<a ', source_link('<test>', url))
        self.assertEqual(source_link('<test>', ''), '&lt;test&gt;')
        self.assertEqual(clean_excerpt('标题；内容；内容', '标题'), '内容')

    @patch('gov_report.report.convert_docx_to_pdf', side_effect=AssertionError('Must not call LibreOffice'))
    def test_export_all_uses_portable_renderer_even_with_office_installed(self, conversion):
        paths = export_all([self.record()], self.root, self.start, self.end, {})
        self.assertTrue(all(Path(p).is_file() for p in paths.values()))
        conversion.assert_not_called()

    def test_fonts_and_license_are_in_source_archive_allowlist(self):
        names = {p.relative_to(ROOT).as_posix() for p in collect_paths(ROOT)}
        for name in ('Regular', 'Medium', 'Bold'):
            self.assertIn(f'assets/fonts/SourceHanSansCN-{name}.ttf', names)
        self.assertIn('assets/fonts/LICENSE.txt', names)

    def test_failed_pdf_build_keeps_previous_report(self):
        path = self.root / 'report.pdf'
        path.write_bytes(b'previous report')
        from gov_report.pdf_report import ReportDocument
        original_build = ReportDocument.build
        calls = []
        def fail_second(document, *args, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError('fixture export error')
            return original_build(document, *args, **kwargs)
        with patch.object(ReportDocument, 'build', fail_second):
            with self.assertRaises(RuntimeError):
                self.export([self.record()])
        self.assertEqual(path.read_bytes(), b'previous report')
        self.assertEqual(list(self.root.glob('.report-*')), [])

    def test_first_page_links_to_final_failure_appendix_and_all_urls_are_clickable(self):
        issues = [dict(url=f'https://example.gov.cn/missing/{i}?a=1&b=2', title=f'访问失败页面{i}',
                       status='detail_failed', reason='HTTP 404：页面不存在') for i in range(35)]
        context = {'coverage': {'partial': 1, 'counts': {'detail_failed': 35, 'skipped_attachment': 18},
                               'sources': [dict(name='测试单位', status='partial', issues=issues)]}}
        reader = self.export([self.record()], context)
        self.assertIn('35 个页面', reader.pages[0].extract_text())
        destinations = [ref.get_object()['/Dest'] for ref in reader.pages[0].get('/Annots', [])
                        if '/Dest' in ref.get_object()]
        appendix = next(i for i,p in enumerate(reader.pages) if '附录 / 访问异常与待核查页面' in p.extract_text())
        self.assertTrue(any(dest[0] == reader.pages[appendix].indirect_reference for dest in destinations))
        urls = [ref.get_object().get('/A', {}).get('/URI') for p in reader.pages[appendix:] for ref in p.get('/Annots', [])]
        for issue in issues:
            self.assertGreaterEqual(urls.count(issue['url']), 2)
        self.assertIn('访问失败页面34', reader.pages[-1].extract_text())


if __name__ == '__main__':
    unittest.main()
