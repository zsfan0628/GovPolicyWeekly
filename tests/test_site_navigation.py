from __future__ import annotations

import tempfile
import json
import unittest
from pathlib import Path
from unittest.mock import Mock

from gov_report.crawler import GovCrawler
from gov_report.date_utils import resolve_date_range
from gov_report.http import HttpClient
from gov_report.parser import (
    discover_channel_urls,
    extract_links,
    extract_pagination_urls,
    extract_redirect_url,
    extract_static_script_urls,
    extract_article,
    script_written_html,
)


class NavigationTests(unittest.TestCase):
    def test_jcms_embedded_records_have_titles_dates_and_next_group(self):
        html = '''<script type="text/xml"><datastore>
        <nextgroup><![CDATA[<a href="/module/web/jpage/dataproxy.jsp?page=1"></a>]]></nextgroup>
        <recordset><record><![CDATA[<li><a href="/art/2026/10/17/art_1_2.html">人事任免通知</a>
        <span>2026-10-17</span></li>]]></record></recordset></datastore></script>'''
        links = extract_links(html, "https://example.gov.cn/col/col1/index.html")
        self.assertEqual([(x.title, x.date_text) for x in links], [("人事任免通知", "2026-10-17")])
        self.assertEqual(extract_pagination_urls(html, "https://example.gov.cn/col/col1/index.html"),
                         ["https://example.gov.cn/module/web/jpage/dataproxy.jsp?page=1"])

    def test_xml_pagination_response_is_parsed_without_running_javascript(self):
        html = '<datastore><recordset><record><![CDATA[<li><a href="/art/2026/10/16/art_1_3.html">行政许可公告</a><span>2026-10-16</span></li>]]></record></recordset></datastore>'
        self.assertEqual(extract_links(html, "https://example.gov.cn/proxy")[0].date_text, "2026-10-16")

    def test_article_and_attachment_links_are_not_discovered_as_channels(self):
        html = '<nav>政策文件<a href="/policies/">政策文件</a><a href="/art/2026/10/17/art_1_2.html">政策通知</a><a href="/policy.pdf">政策文件</a><a href="/news/">普通新闻</a></nav>'
        self.assertEqual(discover_channel_urls(html, "https://example.gov.cn/", max_channels=0),
                         ["https://example.gov.cn/policies/"])
        html = '<a href="/ywjwj2019n1y16rq/tzgg/h5.shtml">通知公告</a>'
        self.assertEqual(discover_channel_urls(html, "https://fgw.hubei.gov.cn/", max_channels=0),
                         ["https://fgw.hubei.gov.cn/ywjwj2019n1y16rq/tzgg/h5.shtml"])

    def test_literal_script_navigation_and_onclick_links(self):
        script = '''document.writeln('<a href="/policies/">政策文件</a>');'''
        self.assertIn('href="/policies/"', script_written_html(script))
        html = f'<script>{script}</script><button onclick="window.location.href=\'/people/\'">人事任免</button>'
        self.assertEqual([x.url for x in extract_links(html, "https://example.gov.cn/")],
                         ["https://example.gov.cn/people/", "https://example.gov.cn/policies/"])

    def test_navigation_dropdown_options_accept_urls_but_not_search_values(self):
        html = '<select><option value="">请选择</option><option value="/policies/">政策文件</option><option value="2026">2026年</option></select>'
        self.assertEqual([x.url for x in extract_links(html, "https://example.gov.cn/")],
                         ["https://example.gov.cn/policies/"])

    def test_redirect_selects_same_host_desktop_target(self):
        html = '<script>if(mobile){window.location.href="https://m.example.gov.cn/index.htm";}else{window.location.href="/index.htm";}</script>'
        self.assertEqual(extract_redirect_url(html, "https://example.gov.cn/"), "https://example.gov.cn/index.htm")
        self.assertIsNone(extract_redirect_url('<script>location.href="https://other.example/";</script>', "https://example.gov.cn/"))

    def test_static_navigation_scripts_do_not_include_analytics_or_libraries(self):
        html = '<script src="/script/0/123456.js"></script><script src="/resource/theme/js/header.js"></script><script src="/jquery.js"></script><script src="https://other.example/header.js"></script>'
        self.assertEqual(extract_static_script_urls(html, "https://example.gov.cn/"),
                         ["https://example.gov.cn/script/0/123456.js", "https://example.gov.cn/resource/theme/js/header.js"])

    def test_pagination_handles_trs_and_rejects_external_or_disabled_next_links(self):
        html = '''<script>createPageHTML(4, 0, "index", "shtml");</script>
        <a href="/ignored" aria-disabled="true">下一页</a><a href="https://other.example/">下一页</a>'''
        self.assertEqual(extract_pagination_urls(html, "https://example.gov.cn/list/index.shtml"),
                         ["https://example.gov.cn/list/index_1.shtml"])
        self.assertEqual(extract_pagination_urls('<script>createPageHTML(4,3,"index","shtml")</script>',
                                                "https://example.gov.cn/list/index_3.shtml"), [])

    def test_trs_variable_based_pagination_is_finite(self):
        html = '''<script>var currentPage = 0;var nextPage = currentPage+1;
        var countPage = 25;document.write('<a href="index.htm">首页</a>');</script>'''
        self.assertEqual(extract_pagination_urls(html, "https://www.moa.gov.cn/xw/zxfb/"),
                         ["https://www.moa.gov.cn/xw/zxfb/index_1.htm"])
        self.assertEqual(extract_pagination_urls(html.replace("currentPage = 0", "currentPage = 24"),
                                                "https://www.moa.gov.cn/xw/zxfb/index_24.htm"), [])

    def test_dynamic_http_200_pages_require_browser_rendering(self):
        self.assertTrue(HttpClient._needs_browser_render('<script src="/AuthorizedRead/unitbuild.js"></script>', "https://www.miit.gov.cn/list/"))
        self.assertTrue(HttpClient._needs_browser_render('<script>loadList()</script>', "https://example.gov.cn/list/"))
        self.assertFalse(HttpClient._needs_browser_render('<a href="/policies/">政策</a>', "https://example.gov.cn/"))
        self.assertTrue(HttpClient._needs_browser_render('<script src="/mainx.js"></script><div class="page-demo"></div><a href="/">首页</a>', "https://yjgl.nantong.gov.cn/list/"))
        self.assertFalse(HttpClient._needs_browser_render('<script src="/mainx.js"></script><div class="page-demo"><a href="/policies/">政策文件</a></div>', "https://yjgl.nantong.gov.cn/list/"))

    def test_truecms_pagination_starts_after_embedded_records(self):
        html = '''<div id="initData"><ul><li>第一条</li></ul><ul><li>第二条</li></ul></div>
        <script>$('#msgList').jpage({totalRecord:3,perPage:1,
        proxyUrl:'/truecms/messageController/getMessage.do',
        ajaxParam:{columnId:'0c41f442-1eed-4eee-8922-dcfabf12a900'}});</script>'''
        urls = extract_pagination_urls(html, "https://yjgl.nantong.gov.cn/ntaj/zcwj/zcwj.html")
        self.assertEqual(len(urls), 1)
        self.assertIn("startrecord=3&endrecord=3&perpage=1", urls[0])
        self.assertIn("callback=govreport", urls[0])
        self.assertEqual(extract_pagination_urls(html.replace("totalRecord:3", "totalRecord:2"),
                                                "https://yjgl.nantong.gov.cn/ntaj/zcwj/zcwj.html"), [])

    def test_truecms_jsonp_is_decoded_as_data_and_preserves_next_group(self):
        response = Mock(url="https://yjgl.nantong.gov.cn/truecms/messageController/getMessage.do?columnId=id&startrecord=11&endrecord=20&perpage=10&callback=govreport")
        xml = '<datastore><totalrecord>24</totalrecord><recordset><record><![CDATA[<li><a href="/ntaj/zcwj/content/abc.html">政策文件通知</a><span>2026-10-16</span></li>]]></record></recordset></datastore>'
        response.text = ";govreport(" + json.dumps({"result": xml}) + ")"
        html = HttpClient.render_truecms_response(response)
        links = extract_links(html, response.url)
        self.assertEqual(links[0].date_text, "2026-10-16")
        self.assertEqual(links[0].title, "政策文件通知")
        self.assertIn("startrecord=21&endrecord=24", extract_pagination_urls(html, response.url)[0])
        response.url = response.url.replace("endrecord=20", "endrecord=24")
        self.assertEqual(extract_pagination_urls(HttpClient.render_truecms_response(response), response.url), [])
        response.text = "maliciousFunction(" + json.dumps({"result": xml}) + ")"
        with self.assertRaises(json.JSONDecodeError):
            HttpClient.render_truecms_response(response)

    def test_miit_grouped_query_preserves_order_dates_and_pagination(self):
        response = Mock(url="https://www.miit.gov.cn/search-front-server/api/search/info?p=1&pg=2")
        response.json.return_value = {"data": {"searchResult": {"total": 3, "dataResults": [
            {"groupData": [{"data": {"title": "第一条政策文件", "url": "/art/2026/art_a.html", "deploytime": "1792144800000"}}]},
            {"groupData": [{"data": {"title": "第二条政策文件", "url": "/art/2026/art_b.html", "deploytime": "1792058400000"}}]},
        ]}}}
        html = HttpClient.render_miit_response(response)
        links = extract_links(html, response.url)
        self.assertEqual([x.title for x in links[:2]], ["第一条政策文件", "第二条政策文件"])
        self.assertEqual(links[0].date_text, "2026-10-16")
        self.assertIn("p=2", extract_pagination_urls(html, response.url)[0])
        response.url = response.url.replace("p=1", "p=2")
        self.assertEqual(extract_pagination_urls(HttpClient.render_miit_response(response), response.url), [])

    def test_miit_unit_pagination_uses_declared_public_metadata(self):
        html = '''<div class="pagination" querydata="{'webId':'site','pageId':'id','tagId':'政策栏目'}"
        rows="24" count="49" pageno="2" uniturl="/api-gateway/jpaas-publish-server/front/page/build/unit"></div>'''
        from urllib.parse import parse_qs, urlparse
        urls = extract_pagination_urls(html, "https://www.miit.gov.cn/xwfb/zxzc/index.html")
        params = parse_qs(urlparse(urls[0]).query)
        self.assertEqual(params["tagId"], ["政策栏目"])
        self.assertEqual(json.loads(params["paramJson"][0]), {"pageNo": 3, "pageSize": "24"})
        self.assertEqual(extract_pagination_urls(html.replace('pageno="2"', 'pageno="3"'), "https://www.miit.gov.cn/list/"), [])
        response = Mock()
        response.json.return_value = {"data": {"html": html}}
        self.assertEqual(HttpClient.render_unit_response(response), html)

    def test_publication_metadata_takes_priority_over_header_calendar(self):
        html = '<meta name="PubDate" content="2026-10-16"><header>2026年10月18日</header><h1>行政许可公告</h1><article>正文。</article>'
        article = extract_article(html, "https://example.gov.cn/article.html")
        self.assertEqual(article.publish_date.strftime("%Y-%m-%d"), "2026-10-16")

    def test_hlj_dynamic_folder_and_more_button_expose_public_get_endpoints(self):
        html = '<div id="websiteCode">nynct</div><meta name="channelId" content="' + "a" * 32 + '"><input id="pageSize" value="15"><div id="page_div"></div><li><a href="javascript:;" data-code="c123" data-channelid="' + "b" * 32 + '">政策文件</a><i class="icon plus"></i><ol></ol></li>'
        links = extract_links(html, "https://nynct.hlj.gov.cn/nynct/c123/zfxxgk.shtml")
        self.assertEqual(len(links), 2)
        self.assertIn("/common/search/" + "b" * 32, links[0].url)
        self.assertIn("channelCode=c123&websiteCodeName=nynct", links[1].url)
        self.assertIn("/common/getChannelList?channelCode=", links[1].url)
        self.assertIn("page=2", extract_pagination_urls(html, "https://nynct.hlj.gov.cn/nynct/c123/public_list.shtml")[0])

    def test_dated_attachment_is_not_an_article_candidate(self):
        from gov_report.parser import LinkItem
        with tempfile.TemporaryDirectory() as folder:
            crawler = GovCrawler([], {}, folder, use_llm=False, sleep=0)
            start, _ = resolve_date_range(start_date="2026-10-16", end_date="2026-10-17")
            item = LinkItem(title="行政许可公告", url="https://example.gov.cn/202610/table.et", publish_date=start)
            self.assertFalse(crawler.should_fetch_candidate(item))

    def test_json_list_adapter_preserves_dates_and_stops_after_last_page(self):
        response = Mock(url="https://nynct.hlj.gov.cn/common/search/id?_pageSize=15&page=1")
        record = {"title": "公告 & 通知", "url": "/nynct/202610/article.shtml", "publishedTimeStr": "2026-10-16 09:00:00"}
        response.json.return_value = {"data": {"results": [record], "page": 1, "rows": 15, "total": 16}}
        html = HttpClient.render_search_response(response)
        links = extract_links(html, response.url)
        self.assertEqual(links[0].title, record["title"])
        self.assertEqual(links[0].date_text, "2026-10-16")
        self.assertIn("page=2", extract_pagination_urls(html, response.url)[0])
        response.json.return_value["data"]["total"] = 1
        self.assertEqual(extract_pagination_urls(HttpClient.render_search_response(response), response.url), [])

    def test_crawler_reaches_nested_channels_and_xml_pagination(self):
        root = "https://example.gov.cn/"
        first = root + "art/2026/10/17/art_1_2.html"
        second = root + "art/2026/10/16/art_1_3.html"
        pages = {
            root: '<a href="/open/">政府信息公开</a>',
            root + "open/": '<a href="/policy/">政策文件</a>',
            root + "policy/": f'<li><a href="{first}">人事任免通知</a><span>2026-10-17</span></li><a rel="next" href="/next">下一页</a>',
            root + "next": f'<li><a href="{second}">行政许可公告</a><span>2026-10-16</span></li>',
            first: '<h1>人事任免通知</h1><p>发布时间：2026-10-17</p><div class="TRS_Editor">人事任免正文。</div>',
            second: '<h1>行政许可公告</h1><p>发布时间：2026-10-16</p><div class="TRS_Editor">行政许可公告正文。</div>',
        }
        source = {"name": "test", "base_url": root, "list_urls": []}
        with tempfile.TemporaryDirectory() as folder:
            crawler = GovCrawler([source], {}, Path(folder), max_channels_per_source=0,
                                 max_detail_per_source=0, use_llm=False, sleep=0)
            crawler.client = Mock()
            crawler.client.fetch_text.side_effect = lambda url: (pages[url], url)
            crawler.log = Mock()
            crawler.decide_with_optional_llm = Mock(return_value={"include": False})
            start, end = resolve_date_range(start_date="2026-10-16", end_date="2026-10-17")
            crawler.crawl_source(source, start, end)
            fetched = [x.args[0] for x in crawler.client.fetch_text.call_args_list]
            self.assertCountEqual(fetched, list(pages))
            self.assertEqual(crawler.decide_with_optional_llm.call_count, 2)

    def test_repeated_pagination_is_not_followed_or_fetched_as_an_article(self):
        root = "https://example.gov.cn/"
        article_url = root + "art/2026/10/17/art_1_2.html"
        row = f'<li><a href="{article_url}">人事任免通知</a><span>2026-10-17</span></li>'
        pages = {root: row + '<a href="/page2" rel="next">下一页</a>',
                 root + "page2": row + '<a href="/page3" rel="next">下一页</a>',
                 article_url: '<h1>人事任免通知</h1><p>发布时间：2026-10-17</p><article>人事任免正文。</article>'}
        with tempfile.TemporaryDirectory() as folder:
            source = {"name": "test", "base_url": root}
            crawler = GovCrawler([source], {}, Path(folder), use_llm=False, sleep=0)
            crawler.client = Mock()
            crawler.client.fetch_text.side_effect = lambda url: (pages[url], url)
            crawler.log = Mock()
            crawler.decide_with_optional_llm = Mock(return_value={"include": False})
            start, end = resolve_date_range(start_date="2026-10-16", end_date="2026-10-17")
            crawler.crawl_source(source, start, end)
            self.assertEqual([x.args[0] for x in crawler.client.fetch_text.call_args_list], list(pages))

    def test_browser_error_page_is_a_failure_and_the_page_is_closed(self):
        client = HttpClient()
        client._browser_context = Mock()
        page = client._browser_context.new_page.return_value
        page.goto.return_value.status = 404
        page.url = "https://example.gov.cn/missing"
        page.title.return_value = "Government website"
        with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
            client._fetch_text_browser(page.url)
        page.close.assert_called_once()

    def test_browser_snapshot_retries_a_navigation_race(self):
        client = HttpClient()
        client._browser_context = Mock()
        page = client._browser_context.new_page.return_value
        page.goto.return_value.status = 200
        page.content.side_effect = [RuntimeError("page is navigating and changing the content"), "<html>正文</html>"]
        page.url = "https://example.gov.cn/"
        page.title.return_value = "Official website"
        self.assertEqual(client._fetch_text_browser(page.url), ("<html>正文</html>", page.url))
        page.wait_for_load_state.assert_any_call("domcontentloaded", timeout=20000)
        page.close.assert_called_once()

    def test_pagination_deduplication_is_scoped_to_each_channel(self):
        root = "https://example.gov.cn/"
        article = root + "art/2026/10/17/art_1_2.html"
        row = f'<li><a href="{article}">人事任免通知</a><span>2026-10-17</span></li>'
        pages = {
            root: '<a href="/one/">政策文件</a><a href="/two/">人事信息</a>',
            root + "one/": row,
            root + "two/": '<a rel="next" href="/two/page2">下一页</a>',
            root + "two/page2": row + '<a rel="next" href="/two/page3">下一页</a>',
            root + "two/page3": "<p>最后一页</p>",
            article: '<h1>人事任免通知</h1><p>发布时间：2026-10-17</p><article>人事任免正文。</article>',
        }
        self.assert_crawler_visits_all(pages, root)

    def test_jcms_first_group_bridge_does_not_hide_later_groups(self):
        root = "https://example.gov.cn/"
        first = root + "art/2026/10/17/art_1_2.html"
        second = root + "art/2026/10/16/art_1_3.html"
        proxy = root + "module/web/jpage/dataproxy.jsp?page="
        row = f'<li><a href="{first}">人事任免通知</a><span>2026-10-17</span></li>'
        pages = {
            root: row + f'<a rel="next" href="{proxy}1">下一页</a>',
            proxy + "1": row + f'<a rel="next" href="{proxy}2">下一页</a>',
            proxy + "2": f'<li><a href="{second}">行政许可公告</a><span>2026-10-16</span></li>',
            first: '<h1>人事任免通知</h1><p>发布时间：2026-10-17</p><article>正文。</article>',
            second: '<h1>行政许可公告</h1><p>发布时间：2026-10-16</p><article>正文。</article>',
        }
        self.assert_crawler_visits_all(pages, root)

    def assert_crawler_visits_all(self, pages, root):
        with tempfile.TemporaryDirectory() as folder:
            source = {"name": "test", "base_url": root}
            crawler = GovCrawler([source], {}, Path(folder), use_llm=False, sleep=0)
            crawler.client = Mock()
            crawler.client.fetch_text.side_effect = lambda url: (pages[url], url)
            crawler.log = Mock()
            crawler.decide_with_optional_llm = Mock(return_value={"include": False})
            start, end = resolve_date_range(start_date="2026-10-16", end_date="2026-10-17")
            crawler.crawl_source(source, start, end)
            self.assertCountEqual([x.args[0] for x in crawler.client.fetch_text.call_args_list], list(pages))


if __name__ == "__main__":
    unittest.main()
