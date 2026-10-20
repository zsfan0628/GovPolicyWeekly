from __future__ import annotations

import unittest

from scripts.audit_sources import inspect_html
from scripts.summarize_source_audit import verified_channels


class AuditSummaryTests(unittest.TestCase):
    def test_download_buttons_are_inventoried_without_being_crawled_as_columns(self):
        result = inspect_html('<a href="/202610/收费目录.et">收费目录文件</a>', "https://example.gov.cn/", "https://example.gov.cn/")
        link = result["links"][0]
        self.assertTrue(link["attachment"])
        self.assertTrue(link["request_excluded"])
        self.assertFalse(link["channel"])
        self.assertFalse(link["article"])

    def test_redirect_aliases_keep_valid_columns_but_not_home_or_login(self):
        root = "https://example.gov.cn/"
        links = [
            {"label": "规范性文件", "url": root + "policies/", "channel": True},
            {"label": "政策文件", "url": root + "old-policies/", "channel": True},
            {"label": "行政许可", "url": root + "login.jsp", "channel": True},
        ]
        article = {"url": root + "art/2026/article.html", "label": "政策通知", "article": True, "same_site": True}
        site = {"source": {"base_url": root}, "pages": {
            root: {"ok": True, "final_url": root, "links": links},
            root + "public/": {"ok": True, "final_url": root + "policies/", "links": [article]},
            root + "old-policies/": {"ok": True, "final_url": root, "links": links},
            root + "login.jsp": {"ok": True, "final_url": root + "login.jsp", "links": [article]},
        }}
        self.assertEqual(verified_channels(site), {root + "policies/": "规范性文件"})

    def test_unrequested_or_empty_shell_is_not_a_verified_collection_seed(self):
        root = "https://example.gov.cn/"
        site = {"source": {"base_url": root}, "pages": {
            root: {"ok": True, "final_url": root, "links": [
                {"label": "政策文件", "url": root + "unrequested/", "channel": True},
                {"label": "通知公告", "url": root + "empty/", "channel": True},
            ]},
            root + "empty/": {"ok": True, "final_url": root + "empty/", "links": []},
        }}
        self.assertEqual(verified_channels(site), {})


if __name__ == "__main__":
    unittest.main()
