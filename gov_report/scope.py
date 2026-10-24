"""Daily crawl scope, kept separate from the full site-audit inventory."""

from __future__ import annotations

import re
from urllib.parse import urlparse


def column_name(value: str) -> str:
    value = re.sub(r"^[\s\-]+|\s+", "", value or "")
    return re.sub(r"(?:更多|子栏目)$", "", value)


def apply_scope(source: dict, policy: dict) -> dict:
    result = dict(source)
    names = {column_name(name) for name in policy.get("column_names", [])}
    labels = source.get("channel_names", {})
    urls = [url for url in source.get("list_urls", []) if column_name(labels.get(url, "")) in names]
    # Custom sources without named columns retain discovery rather than silently losing coverage.
    if urls:
        result["crawl_scope"] = {"urls": urls, "column_names": sorted(names),
                                 "date_stop": bool(policy.get("date_stop", True)),
                                 "old_pages_required": max(2, int(policy.get("old_pages_required", 2))),
                                 "minimum_pages": max(3, int(policy.get("minimum_pages", 3)))}
    return result


def core_urls(source: dict, full_scan: bool = False) -> list[str]:
    scope = source.get("crawl_scope", {}) if not full_scan else {}
    return list(scope.get("urls") or [source["base_url"], *source.get("list_urls", [])])


def channel_allowed(source: dict, url: str, label: str, full_scan: bool = False) -> bool:
    scope = source.get("crawl_scope", {}) if not full_scan else {}
    if not scope:
        return True
    if url in scope["urls"]:
        return True
    if column_name(label) not in scope["column_names"]:
        return False
    target = urlparse(url)
    # Follow named subcolumns inside a core branch, not unrelated links in the global menu.
    for root in scope["urls"]:
        seed = urlparse(root)
        parent = seed.path if seed.path.endswith("/") else seed.path.rsplit("/", 1)[0] + "/"
        if target.netloc == seed.netloc and parent != "/" and target.path.startswith(parent):
            return True
    return False
