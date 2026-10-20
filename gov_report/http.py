from __future__ import annotations

import mimetypes
import json
import os
import re
import sys
import time
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .parser import extract_redirect_url, extract_static_script_urls, navigation_soup, script_written_html
from .date_utils import TZ


class HttpClient:
    def __init__(self, timeout: int = 20, sleep: float = 0.5, verify_ssl: bool = True, browser_fallback: bool = False) -> None:
        self.timeout = timeout
        self.sleep = sleep
        self.verify_ssl = verify_ssl
        self.browser_fallback = browser_fallback
        self.session = requests.Session()
        self._navigation_cache: dict[str, str] = {}
        self._playwright_runtime = None
        self._browser = None
        self._browser_context = None
        retry = Retry(
            total=2,
            connect=2,
            read=2,
            backoff_factor=0.8,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET", "HEAD"),
        )
        adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        # 政府网站常见 CDN/WAF 会校验浏览器请求头。
        # 这里尽量模拟正常 Chrome 访问，避免 403/412。
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Cache-Control": "max-age=0",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
            }
        )

    def fetch_text(self, url: str) -> tuple[str, str]:
        errors: list[str] = []
        for try_url in self._candidate_urls(url):
            try:
                html, final_url = self._fetch_text_requests(try_url)
                if self.browser_fallback and self._needs_browser_render(html, final_url):
                    return self._fetch_text_browser(final_url)
                return html, final_url
            except Exception as e:
                errors.append(f"{try_url} -> {e}")
                if self.browser_fallback and self._should_try_browser(e):
                    try:
                        return self._fetch_text_browser(try_url)
                    except Exception as be:
                        errors.append(f"browser:{try_url} -> {be}")
        raise RuntimeError("; ".join(errors[-4:]))

    def _fetch_text_requests(self, url: str, _visited: set[str] | None = None) -> tuple[str, str]:
        visited = set() if _visited is None else _visited
        if url in visited or len(visited) >= 5:
            raise RuntimeError(f"页面脚本跳转循环: {url}")
        visited.add(url)
        time.sleep(self.sleep)
        headers = {"Referer": self._referer_for(url)}
        resp = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl, headers=headers, allow_redirects=True)
        resp.raise_for_status()

        if urlparse(resp.url).path.startswith("/common/search/"):
            return self.render_search_response(resp), resp.url
        if urlparse(resp.url).path == "/common/getChannelList":
            return self.render_channel_response(resp), resp.url
        if urlparse(resp.url).path == "/truecms/messageController/getMessage.do":
            return self.render_truecms_response(resp), resp.url
        if urlparse(resp.url).path == "/search-front-server/api/search/info":
            return self.render_miit_response(resp), resp.url
        if urlparse(resp.url).path == "/api-gateway/jpaas-publish-server/front/page/build/unit":
            return self.render_unit_response(resp), resp.url

        # 有些政府站点的附件链接也会被列表页抓到，甚至返回 .doc/.wps/.pdf 二进制内容。
        # 这些内容如果误当网页正文写入 Excel，会触发 openpyxl IllegalCharacterError。
        if self._looks_like_binary_response(resp):
            raise RuntimeError(f"非HTML页面/疑似附件二进制内容，跳过: {resp.url}")

        if not resp.encoding or resp.encoding.lower() in {"iso-8859-1", "ascii"}:
            resp.encoding = resp.apparent_encoding or "utf-8"
        redirect = extract_redirect_url(resp.text, resp.url)
        if redirect:
            return self._fetch_text_requests(redirect, visited)
        return self.expand_navigation(resp.text, resp.url), resp.url

    @staticmethod
    def render_unit_response(response) -> str:
        html = (response.json().get("data") or {}).get("html")
        if not isinstance(html, str) or not html.strip():
            raise RuntimeError(f"动态栏目接口返回了无法识别的数据: {response.url}")
        return html

    @staticmethod
    def render_miit_response(response) -> str:
        payload = response.json()
        result = (payload.get("data") or {}).get("searchResult")
        if not isinstance(result, dict) or not isinstance(result.get("dataResults"), list):
            raise RuntimeError(f"政策文件库接口返回了无法识别的数据: {response.url}")
        pending = list(result["dataResults"])
        rows = []
        while pending:
            node = pending.pop()
            pending.extend(node.get("groupData") or [])
            record = node.get("data") or {}
            url, title = record.get("url"), record.get("title")
            if not url or not title:
                continue
            published = record.get("deploytime") or record.get("publishtime") or ""
            date = datetime.fromtimestamp(int(published) / 1000, TZ).strftime("%Y-%m-%d") if str(published).isdigit() else str(published)[:10]
            rows.append(f'<li><a href="{escape(urljoin(response.url, url), quote=True)}">{escape(title)}</a><span>{escape(date)}</span></li>')
        rows.reverse()
        params = dict(parse_qsl(urlparse(response.url).query, keep_blank_values=True))
        page, size = int(params.get("p") or 1), int(params.get("pg") or 10)
        if rows and page * size < int(result.get("total", 0)):
            params["p"] = str(page + 1)
            next_url = urlunparse(urlparse(response.url)._replace(query=urlencode(params)))
            rows.append(f'<a rel="next" href="{escape(next_url, quote=True)}">下一页</a>')
        return '<html><head><title>政策文件库查询结果</title></head><body><ul>' + "\n".join(rows) + '</ul></body></html>'

    @staticmethod
    def render_truecms_response(response) -> str:
        text = response.text.strip()
        wrapper = re.fullmatch(r";?\s*govreport\((.*)\)\s*;?", text, re.S)
        payload = json.loads(wrapper[1] if wrapper else text)
        xml = payload.get("result")
        if not isinstance(xml, str) or "<datastore" not in xml:
            raise RuntimeError(f"TrueCMS 列表接口返回了无法识别的数据: {response.url}")
        soup = navigation_soup(xml)
        total_node = soup.find("totalrecord")
        if total_node is None or not total_node.get_text(strip=True).isdigit():
            raise RuntimeError(f"TrueCMS 列表缺少记录总数: {response.url}")
        params = dict(parse_qsl(urlparse(response.url).query, keep_blank_values=True))
        end = int(params["endrecord"])
        size = max(1, int(params["perpage"]))
        total = int(total_node.get_text(strip=True))
        if soup.find("record") is not None and end < total:
            params.update(startrecord=str(end + 1), endrecord=str(min(end + size, total)))
            next_url = urlunparse(urlparse(response.url)._replace(query=urlencode(params)))
            anchor = soup.new_tag("a", href=next_url, rel="next")
            anchor.string = "下一页"
            (soup.body or soup).append(anchor)
        return str(soup)

    @staticmethod
    def render_channel_response(response) -> str:
        result = response.json().get("results")
        if not isinstance(result, dict):
            raise RuntimeError(f"栏目目录接口返回了无法识别的数据: {response.url}")
        rows = []
        params = dict(parse_qsl(urlparse(response.url).query))
        nodes = [result] + (result.get("children") or [])
        for node in nodes:
            channel_id, label = node.get("channelId", ""), node.get("channelName", "")
            if not channel_id or not label:
                continue
            query = urlencode({"_isAgg": "true", "_isJson": "true", "_pageSize": 15, "_template": "index", "page": 1})
            url = urljoin(response.url, f"/common/search/{channel_id}?{query}")
            rows.append(f'<li><a href="{escape(url, quote=True)}">{escape(label)}</a></li>')
            if node is not result and node.get("isChildren"):
                query = urlencode({"channelCode": node["channelCode"], "websiteCodeName": params.get("websiteCodeName", "")})
                url = urljoin(response.url, f"/common/getChannelList?{query}")
                rows.append(f'<li><a href="{escape(url, quote=True)}">{escape(label)}子栏目</a></li>')
        return '<html><head><title>政府信息公开栏目目录</title></head><body><ul>' + "\n".join(rows) + '</ul></body></html>'

    @staticmethod
    def render_search_response(response) -> str:
        payload = response.json()
        data = payload.get("data", {})
        records = data.get("results")
        if not isinstance(records, list):
            raise RuntimeError(f"公开列表接口返回了无法识别的数据: {response.url}")
        rows = []
        for record in records:
            url = record.get("url", "")
            title = record.get("title", "")
            if url and title:
                date = str(record.get("publishedTimeStr") or record.get("publishDate") or "")[:10]
                rows.append(f'<li><a href="{escape(urljoin(response.url, url), quote=True)}">{escape(str(title))}</a><span>{escape(date)}</span></li>')
        params = dict(parse_qsl(urlparse(response.url).query, keep_blank_values=True))
        page = int(data.get("page", params.get("page", 1)))
        size = int(data.get("rows", params.get("_pageSize", 15)))
        total = int(data.get("total", len(records)))
        if records and page * size < total:
            params["page"] = str(page + 1)
            parsed = urlparse(response.url)
            next_url = urlunparse(parsed._replace(query=urlencode(params)))
            rows.append(f'<a rel="next" href="{escape(next_url, quote=True)}">下一页</a>')
        return '<html><head><title>政府信息公开列表</title></head><body><ul>' + "\n".join(rows) + '</ul></body></html>'

    def expand_navigation(self, html: str, base_url: str) -> str:
        fragments = []
        for url in extract_static_script_urls(html, base_url):
            if url not in self._navigation_cache:
                try:
                    time.sleep(self.sleep)
                    response = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl,
                                                headers={"Referer": base_url})
                    response.raise_for_status()
                    if not response.encoding or response.encoding.lower() in {"iso-8859-1", "ascii"}:
                        response.encoding = response.apparent_encoding or "utf-8"
                    self._navigation_cache[url] = script_written_html(response.text)
                except requests.RequestException:
                    self._navigation_cache[url] = ""
            if self._navigation_cache[url]:
                fragments.append(self._navigation_cache[url])
        if fragments:
            soup = BeautifulSoup(html, "lxml")
            container = soup.new_tag("div", attrs={"data-extracted-navigation": "true"})
            for fragment in fragments:
                parsed = BeautifulSoup(fragment, "lxml")
                for node in list((parsed.body or parsed).contents):
                    container.append(node.extract())
            (soup.body or soup).append(container)
            html = str(soup)
        return html

    @staticmethod
    def _needs_browser_render(html: str, url: str) -> bool:
        if "AuthorizedRead/unitbuild.js" in html:
            return True
        if "hlj.gov.cn" in url and "zfxxgk.shtml" in url:
            return True
        soup = BeautifulSoup(html, "lxml")
        if urlparse(url).hostname == "www.miit.gov.cn" and soup.find(id="search-form") and not soup.select_one(".search-list-t a"):
            return True
        menu = soup.select_one(".page-demo")
        if "mainx.js" in html and menu is not None and menu.find("a", href=True) is None:
            return True
        return not soup.find("a", href=True) and soup.find("script") is not None and len(soup.get_text(strip=True)) < 200

    def _looks_like_binary_response(self, resp) -> bool:
        content_type = (resp.headers.get("content-type") or "").lower().split(";")[0].strip()
        path = urlparse(resp.url).path.lower()
        binary_exts = (
            ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".wps", ".et",
            ".zip", ".rar", ".7z", ".png", ".jpg", ".jpeg", ".gif", ".mp4", ".avi"
        )
        if path.endswith(binary_exts):
            return True
        text_types = {"", "text/html", "application/xhtml+xml", "application/xml", "text/xml", "text/plain"}
        if content_type and content_type not in text_types and not content_type.endswith("+xml"):
            return True
        head = resp.content[:16]
        binary_magic = (b"%PDF", b"PK\x03\x04", b"\xd0\xcf\x11\xe0", b"Rar!", b"7z\xbc\xaf")
        return any(head.startswith(m) for m in binary_magic)

    def _candidate_urls(self, url: str) -> list[str]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return [url]
        alt_scheme = "https" if parsed.scheme == "http" else "http"
        alt = urlunparse((alt_scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, parsed.fragment))
        # 先按用户配置访问，失败再试 http/https 互换。
        return [url, alt] if alt != url else [url]

    def _referer_for(self, url: str) -> str:
        p = urlparse(url)
        if not p.scheme or not p.netloc:
            return ""
        return f"{p.scheme}://{p.netloc}/"

    def _should_try_browser(self, exc: Exception) -> bool:
        msg = str(exc)
        return any(x in msg for x in ["403", "412", "Precondition Failed", "Forbidden", "Redirect", "重定向"])

    def _fetch_text_browser(self, url: str) -> tuple[str, str]:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as e:
            raise RuntimeError("未安装 Playwright。可执行：pip install playwright && playwright install chromium") from e

        if self._browser_context is None:
            p = sync_playwright().start()
            self._playwright_runtime = p
            launch_options = {"headless": True}
            browser_executable = self._browser_executable_path()
            if browser_executable:
                launch_options["executable_path"] = browser_executable
            try:
                browser = p.chromium.launch(**launch_options)
            except Exception as e:
                fallback_executable = self._browser_executable_path(force_system=True)
                if not fallback_executable or fallback_executable == browser_executable:
                    raise e
                browser = p.chromium.launch(headless=True, executable_path=fallback_executable)
            self._browser = browser
            self._browser_context = browser.new_context(
                locale="zh-CN",
                user_agent=self.session.headers.get("User-Agent"),
                extra_http_headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
            )
        page = self._browser_context.new_page()
        query_urls = []

        def remember_public_query(request):
            parsed = urlparse(request.url)
            if request.method == "GET" and parsed.hostname == "www.miit.gov.cn" and parsed.path == "/search-front-server/api/search/info":
                query_urls.append(request.url)

        page.on("request", remember_public_query)
        try:
            response = page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            for attempt in range(3):
                try:
                    html = page.content()
                    title = page.title().lower()
                    final_url = page.url
                    break
                except Exception as exc:
                    if attempt == 2 or "navigat" not in str(exc).lower():
                        raise
                    page.wait_for_load_state("domcontentloaded", timeout=self.timeout * 1000)
            if response and response.status >= 400 and response.status not in (403, 412):
                raise RuntimeError(f"浏览器访问返回 HTTP {response.status}: {final_url}")
            if title.strip() in {"403", "404", "412", "500"} or (
                any(word in title for word in ("412", "403 forbidden", "access denied", "验证码", "安全验证"))
                and page.locator("a[href]").count() < 2
            ):
                raise RuntimeError(f"浏览器仍未通过站点访问校验: {final_url}")
            for query_url in dict.fromkeys(query_urls):
                parsed = urlparse(query_url)
                params = dict(parse_qsl(parsed.query, keep_blank_values=True))
                params["p"] = str(int(params.get("p") or 1) + 1)
                next_url = urlunparse(parsed._replace(query=urlencode(params)))
                html += f'<a rel="next" data-public-query="true" href="{escape(next_url, quote=True)}">下一页</a>'
            return html, final_url
        finally:
            page.close()

    def close_browser(self) -> None:
        try:
            if self._browser:
                self._browser.close()
        finally:
            if self._playwright_runtime:
                self._playwright_runtime.stop()
            self._browser_context = self._browser = self._playwright_runtime = None

    @staticmethod
    def _browser_executable_path(force_system: bool = False) -> str | None:
        env_path = os.environ.get("GOV_REPORT_BROWSER_EXECUTABLE", "").strip()
        if env_path and Path(env_path).exists():
            return env_path
        if not force_system and env_path:
            return None
        if sys.platform == "darwin":
            for candidate in (
                Path("/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ):
                if candidate.exists():
                    return str(candidate)
        if not sys.platform.startswith("win"):
            return None

        program_files = [
            os.environ.get("PROGRAMFILES", r"C:\Program Files"),
            os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        relative_paths = [
            r"Microsoft\Edge\Application\msedge.exe",
            r"Google\Chrome\Application\chrome.exe",
            r"Chromium\Application\chrome.exe",
        ]
        for root in program_files:
            if not root:
                continue
            for relative in relative_paths:
                candidate = Path(root) / relative
                if candidate.exists():
                    return str(candidate)
        return None

    def download(self, url: str, out_dir: str | Path, filename_hint: str | None = None) -> Path | None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        try:
            time.sleep(self.sleep)
            resp = self.session.get(url, timeout=self.timeout, stream=True, verify=self.verify_ssl)
            resp.raise_for_status()
        except Exception:
            return None

        parsed = urlparse(resp.url)
        name = Path(parsed.path).name
        if not name or "." not in name:
            content_type = resp.headers.get("content-type", "").split(";")[0].strip()
            ext = mimetypes.guess_extension(content_type) or ".bin"
            name = (filename_hint or "attachment") + ext
        name = sanitize_filename(name)
        path = out_dir / name
        base = path.stem
        suffix = path.suffix
        idx = 1
        while path.exists():
            path = out_dir / f"{base}_{idx}{suffix}"
            idx += 1
        with path.open("wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 128):
                if chunk:
                    f.write(chunk)
        return path


def sanitize_filename(name: str, max_len: int = 120) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    for ch in bad:
        name = name.replace(ch, "_")
    name = name.strip(" ._") or "file"
    if len(name) > max_len:
        stem = Path(name).stem[: max_len - 10]
        suffix = Path(name).suffix[:10]
        name = stem + suffix
    return name
