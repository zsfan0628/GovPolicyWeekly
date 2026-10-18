from __future__ import annotations

import mimetypes
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class HttpClient:
    def __init__(self, timeout: int = 20, sleep: float = 0.5, verify_ssl: bool = True, browser_fallback: bool = False) -> None:
        self.timeout = timeout
        self.sleep = sleep
        self.verify_ssl = verify_ssl
        self.browser_fallback = browser_fallback
        self.session = requests.Session()
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
                return self._fetch_text_requests(try_url)
            except Exception as e:
                errors.append(f"{try_url} -> {e}")
                if self.browser_fallback and self._should_try_browser(e):
                    try:
                        return self._fetch_text_browser(try_url)
                    except Exception as be:
                        errors.append(f"browser:{try_url} -> {be}")
        raise RuntimeError("; ".join(errors[-4:]))

    def _fetch_text_requests(self, url: str) -> tuple[str, str]:
        time.sleep(self.sleep)
        headers = {"Referer": self._referer_for(url)}
        resp = self.session.get(url, timeout=self.timeout, verify=self.verify_ssl, headers=headers, allow_redirects=True)
        resp.raise_for_status()

        # 有些政府站点的附件链接也会被列表页抓到，甚至返回 .doc/.wps/.pdf 二进制内容。
        # 这些内容如果误当网页正文写入 Excel，会触发 openpyxl IllegalCharacterError。
        if self._looks_like_binary_response(resp):
            raise RuntimeError(f"非HTML页面/疑似附件二进制内容，跳过: {resp.url}")

        if not resp.encoding or resp.encoding.lower() in {"iso-8859-1", "ascii"}:
            resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text, resp.url

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

        with sync_playwright() as p:
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
            context = browser.new_context(
                locale="zh-CN",
                user_agent=self.session.headers.get("User-Agent"),
                extra_http_headers={
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                },
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout * 1000)
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            html = page.content()
            final_url = page.url
            context.close()
            browser.close()
            return html, final_url

    @staticmethod
    def _browser_executable_path(force_system: bool = False) -> str | None:
        env_path = os.environ.get("GOV_REPORT_BROWSER_EXECUTABLE", "").strip()
        if env_path and Path(env_path).exists():
            return env_path
        if not force_system and env_path:
            return None
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
