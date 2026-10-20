"""Inspect public source navigation and controls and retain reproducible evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import requests
import yaml
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gov_report.http import HttpClient
from gov_report.parser import (ATTACHMENT_EXTS, clean_text, extract_links, extract_pagination_urls, extract_redirect_url,
                               is_probably_article_url, navigation_soup, normalize_url, same_site)

SKIP_PATHS = re.compile(r"(?:logout|signout|delete|unsubscribe|\.(?:pdf|docx?|xlsx?|wps|et|zip|rar|7z|jpe?g|png)(?:$|\?))", re.I)
NAV_TEXT = re.compile(r"首页|机构|领导|新闻|动态|公开|政策|法规|规章|文件|公告|公示|通知|人事|任免|解读|服务|办事|互动|交流|咨询|征集|调查|专题|专栏|数据|统计|规划|计划|财政|预算|决算|采购|许可|审批|标准|监管|执法|权责|建议|提案|地图|指南|目录|年度报告")
PAGE_TEXT = re.compile(r"^(?:下一页|下页|末页|尾页|最后一页|Next|Last|[>»]+)$", re.I)
JS_URL = re.compile(r"(?:window\.open\s*\(|(?:window\.)?location(?:\.href)?\s*=\s*)['\"]([^'\"]+)['\"]", re.I)


def write_report(path: Path, report: dict) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def inspect_html(html: str, url: str, source_url: str) -> dict:
    soup = navigation_soup(html)
    title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    links = []
    for node in soup.select("a[href], area[href], [onclick]"):
        label = clean_text(node.get("title") or node.get("aria-label") or node.get_text(" ", strip=True))
        href = node.get("href", "")
        if not href or href.startswith(("javascript:", "#")):
            match = JS_URL.search(node.get("onclick", ""))
            href = match.group(1) if match else href
        target = normalize_url(href, url)
        if not target:
            continue
        inside = same_site(target, source_url)
        excluded = bool(SKIP_PATHS.search(target))
        attachment = Path(urlparse(target).path).suffix.lower() in ATTACHMENT_EXTS
        article = not excluded and is_probably_article_url(target)
        pagination = bool(PAGE_TEXT.match(label)) or node.get("rel") == ["next"]
        in_nav = node.find_parent(["nav", "header"]) is not None or node.find_parent(
            class_=re.compile(r"nav|menu|page-demo|list3-detail|sidebar", re.I),
        ) is not None
        channel = inside and not excluded and not article and bool(label) and len(label) <= 32 and (
            bool(NAV_TEXT.search(label)) or in_nav or (urlparse(target).path.endswith("/") and label not in {"更多", "查看更多"})
        )
        links.append({"label": label[:180], "url": target, "same_site": inside,
                      "article": article, "channel": channel, "pagination": pagination,
                      "attachment": attachment, "request_excluded": excluded})
    known = {(x["url"], x["label"]) for x in links}
    for item in extract_links(html, url, only_same_site=False, _soup=soup):
        if (item.url, item.title) not in known and not SKIP_PATHS.search(item.url):
            inside = same_site(item.url, source_url)
            article = is_probably_article_url(item.url)
            links.append({"label": item.title, "url": item.url, "same_site": inside,
                          "article": article, "channel": inside and not article and bool(NAV_TEXT.search(item.title)),
                          "pagination": False})
            known.add((item.url, item.title))

    controls = []
    for node in soup.select("button, input, select, textarea, form, [role=tab], [role=button], [onclick], [aria-expanded], [data-toggle], a[href^='javascript:'], .page-demo .xlcd, .search-flbox-btn [sval], .search-flbox-btn [sbeign], #pagination [paged]"):
        kind = node.name
        controls.append({
            "tag": kind, "type": node.get("type", ""), "name": node.get("name", ""),
            "id": node.get("id", ""), "role": node.get("role", ""),
            "label": clean_text(node.get("aria-label") or node.get("placeholder") or node.get("value") or node.get_text(" ", strip=True))[:250],
            "action": normalize_url(node.get("action", ""), url) if kind == "form" else "",
            "method": node.get("method", "get").upper() if kind == "form" else "",
            "onclick": node.get("onclick", "")[:500],
            "data_attributes": {k: v for k, v in node.attrs.items() if k.startswith("data-")},
            "parameters": {k: node[k] for k in ("sval", "sbeign", "send", "paged") if node.has_attr(k)},
            "options": [{"label": clean_text(x.get_text(" ", strip=True)), "value": x.get("value", "")} for x in node.find_all("option")] if kind == "select" else [],
            "execution": "inventoried_not_submitted",
        })
    frames = [normalize_url(x.get("src", ""), url) for x in soup.find_all("iframe")]
    scripts = [normalize_url(x.get("src", ""), url) for x in soup.find_all("script", src=True)]
    script_markers = sorted({m.group(0) for m in re.finditer(r"createPageHTML|createPage|jcms|dataproxy|ajax|fetch\(|axios|layui|laypage|pagination|nextPage|loadMore|通用信息公开", html, re.I)})
    metas = {x.get("name", ""): x.get("content", "") for x in soup.find_all("meta") if x.get("name", "").lower() in {"columntype", "columnname", "columnid", "articletitle"}}
    return {"title": title, "links": links, "controls": controls, "iframes": frames,
            "scripts": scripts, "dynamic_markers": script_markers, "metadata": metas,
            "pagination_urls": extract_pagination_urls(html, url, _soup=soup)}


def fetch_page(client: HttpClient, url: str, directory: Path, timeout: int, browser: bool, cache: dict | None = None) -> dict:
    if cache and url in cache:
        previous, snapshot = cache[url]
        if snapshot.exists():
            result = dict(previous)
            text = snapshot.read_text(encoding="utf-8")
            rendered = any(x.get("method", "").startswith("browser") for x in result.get("attempts", []))
            if browser and not rendered and client._needs_browser_render(text, result["final_url"]):
                try:
                    text, final_url = client._fetch_text_browser(result["final_url"])
                except Exception as exc:
                    return {"url": url, "ok": False, "attempts": [{"method": "browser_rescan", "error": str(exc)[:500]}]}
                result["final_url"] = final_url
                result["attempts"] = list(result.get("attempts", [])) + [{"method": "browser_rescan", "final_url": final_url}]
                (directory / snapshot.name).write_text(text, encoding="utf-8")
            else:
                shutil.copyfile(snapshot, directory / snapshot.name)
            result.update({"html": text, "cached_from": str(snapshot)})
            return result
    attempts = []
    candidates = [url]
    if url.startswith("http://"):
        candidates.insert(0, "https://" + url[7:])
    for candidate in dict.fromkeys(candidates):
        started = time.monotonic()
        try:
            response = client.session.get(candidate, timeout=(8, timeout), allow_redirects=True,
                                          headers={"Referer": client._referer_for(candidate)})
            attempt = {"url": candidate, "status": response.status_code, "final_url": response.url,
                       "elapsed_seconds": round(time.monotonic() - started, 2)}
            attempts.append(attempt)
            if response.status_code >= 400:
                continue
            if not response.encoding or response.encoding.lower() in {"iso-8859-1", "ascii"}:
                response.encoding = response.apparent_encoding or "utf-8"
            text = response.text
            final_url = response.url
            if urlparse(final_url).path.startswith("/common/search/"):
                text = client.render_search_response(response)
            elif urlparse(final_url).path == "/common/getChannelList":
                text = client.render_channel_response(response)
            elif urlparse(final_url).path == "/truecms/messageController/getMessage.do":
                text = client.render_truecms_response(response)
            elif urlparse(final_url).path == "/search-front-server/api/search/info":
                text = client.render_miit_response(response)
            elif urlparse(final_url).path == "/api-gateway/jpaas-publish-server/front/page/build/unit":
                text = client.render_unit_response(response)
            redirect = extract_redirect_url(text, final_url)
            if redirect:
                text, final_url = client._fetch_text_requests(redirect)
                attempts.append({"method": "static_redirect", "url": redirect, "final_url": final_url})
            else:
                text = client.expand_navigation(text, final_url)
            if browser and client._needs_browser_render(text, final_url):
                text, final_url = client._fetch_text_browser(final_url)
                attempts.append({"method": "browser_render", "final_url": final_url})
            filename = hashlib.sha256(url.encode()).hexdigest()[:16] + ".html"
            (directory / filename).write_text(text, encoding="utf-8")
            return {"url": url, "ok": True, "final_url": final_url,
                    "status": response.status_code, "bytes": len(response.content),
                    "snapshot": filename, "attempts": attempts, "html": text}
        except Exception as exc:
            attempts.append({"url": candidate, "error": str(exc)[:500],
                             "elapsed_seconds": round(time.monotonic() - started, 2)})
    if browser:
        try:
            text, final_url = client._fetch_text_browser(candidates[0])
            filename = hashlib.sha256(url.encode()).hexdigest()[:16] + ".html"
            (directory / filename).write_text(text, encoding="utf-8")
            attempts.append({"method": "browser_fallback", "final_url": final_url})
            return {"url": url, "ok": True, "final_url": final_url, "status": None,
                    "bytes": len(text.encode("utf-8")), "snapshot": filename, "attempts": attempts, "html": text}
        except Exception as exc:
            attempts.append({"method": "browser_fallback", "error": str(exc)[:500]})
    return {"url": url, "ok": False, "attempts": attempts}


def audit_source(index: int, source: dict, args) -> dict:
    directory = args.output / f"{index:02d}"
    directory.mkdir(parents=True, exist_ok=True)
    client = HttpClient(timeout=args.timeout, sleep=0)
    for adapter in client.session.adapters.values():
        adapter.max_retries.total = 0
    root = source["base_url"]
    cache = {}
    for cache_dir in args.resume_from:
        path = cache_dir / f"{index:02d}" / "audit.json"
        if path.exists():
            try:
                previous = json.loads(path.read_text(encoding="utf-8"))
                for page in previous["pages"]:
                    if page.get("ok") and page.get("snapshot"):
                        cache[page["url"]] = (page, path.parent / page["snapshot"])
            except (ValueError, KeyError):
                pass
    pending = deque([(root, 0, "homepage")])
    if not args.homepage_only:
        pending.extend((x, 1, "configured_channel") for x in source.get("list_urls", []))
    visited = set()
    pages = []
    while pending and (not args.max_pages or len(pages) < args.max_pages):
        url, depth, reason = pending.popleft()
        if url in visited:
            continue
        visited.add(url)
        result = fetch_page(client, url, directory, args.timeout, args.browser, cache)
        result.update({"depth": depth, "reason": reason})
        if result["ok"]:
            html = result.pop("html")
            result.update(inspect_html(html, result["final_url"], root))
            visited.add(result["final_url"])
            if not args.homepage_only and depth < args.depth:
                for link in result["links"]:
                    if link["channel"] and link["url"] not in visited:
                        pending.append((link["url"], depth + 1, "discovered_channel"))
            if not args.homepage_only and reason not in {"pagination_sample", "article_sample"}:
                pending.extend((x, depth, "pagination_sample") for x in result["pagination_urls"][:1])
                for frame in result["iframes"]:
                    if frame and same_site(frame, root) and not re.search(r"visit|count|wgy|video", frame, re.I):
                        pending.append((frame, depth, "embedded_frame"))
            if not args.homepage_only and args.articles and reason != "article_sample":
                articles = [x for x in result["links"] if x["article"] and x["same_site"]]
                pending.extend((x["url"], depth, "article_sample") for x in articles[:args.articles])
        pages.append(result)
        if len(pages) % 10 == 0 or len(pages) == 1:
            write_report(directory / "audit.json", {"source": source, "pages": pages})
        if len(pages) % 10 == 0:
            print(f"[{index:02d}] {source['name']}: {len(pages)} pages, {len(pending)} pending", flush=True)
        if args.pause and not result.get("cached_from"):
            time.sleep(args.pause)
    remaining = sorted({x[0] for x in pending if x[0] not in visited})
    report = {"source": source, "pages": pages, "unvisited_urls": remaining,
              "complete_within_depth": not remaining and all(x["ok"] for x in pages), "depth": args.depth,
              "navigation_exhausted": not remaining, "controls_submitted": False,
              "success_pages": sum(bool(x["ok"]) for x in pages),
              "failed_pages": sum(not x["ok"] for x in pages)}
    write_report(directory / "audit.json", report)
    client.close_browser()
    print(f"[{index:02d}] {source['name']}: done, {report['success_pages']} accessible / {len(pages)} checked; {len(remaining)} unvisited", flush=True)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", type=Path, default=ROOT / "config/sources.yaml")
    parser.add_argument("--output", type=Path, default=ROOT / "audit-results" / datetime.now().strftime("%Y-%m-%d"))
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--max-pages", type=int, default=0, help="0 means no page cap; the report records any unvisited URLs")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout", type=int, default=15)
    parser.add_argument("--pause", type=float, default=0.2)
    parser.add_argument("--articles", type=int, default=0, help="Article samples to inspect per channel")
    parser.add_argument("--browser", action="store_true", help="Render dynamic pages and retry access failures using the app browser fallback")
    parser.add_argument("--homepage-only", action="store_true", help="Recheck selected homepages without following configured lists or navigation")
    parser.add_argument("--resume-from", type=Path, action="append", default=[], help="Reuse successful snapshots from an earlier pass and inspect newly exposed controls")
    parser.add_argument("--site", type=int, action="append", help="One-based source index; repeat to select sites")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    sources = yaml.safe_load(args.sources.read_text(encoding="utf-8"))
    selected = [(i, s) for i, s in enumerate(sources, 1) if not args.site or i in args.site]
    reports = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        tasks = {executor.submit(audit_source, i, s, args): i for i, s in selected}
        for task in as_completed(tasks):
            report = task.result()
            report["index"] = tasks[task]
            reports.append(report)
    summary = {"checked_at": datetime.now().astimezone().isoformat(),
               "scope": "Public navigation to configured depth; controls inventoried without submitting forms",
               "sites": sorted(reports, key=lambda x: x["index"])}
    write_report(args.output / "audit.json", summary)


if __name__ == "__main__":
    main()
