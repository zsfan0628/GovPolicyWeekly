from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag

from bs4 import BeautifulSoup

from .date_utils import parse_cn_date

ATTACHMENT_EXTS = {
    ".pdf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
    ".rar",
    ".7z",
    ".wps",
    ".et",
}

CHANNEL_KEYWORDS = [
    "通知公告",
    "公告公示",
    "公告",
    "通知",
    "政策",
    "政策文件",
    "法规",
    "文件",
    "人事",
    "任免",
    "公示",
    "行政许可",
    "政务公开",
    "政府信息公开",
    "信息公开",
    "政策解读",
]

BAD_LINK_PREFIXES = ("javascript:", "mailto:", "tel:", "#")

GENERIC_TITLE_PARTS = [
    "网站首页",
    "首页",
    "湖北省经济和信息化厅",
    "中华人民共和国生态环境部",
    "您访问的链接即将离开",
]

ARTICLE_URL_PATTERNS = [
    re.compile(r"/t20\d{6}_\d+\.(?:shtml|html|htm)$", re.I),
    re.compile(r"/art/20\d{2}/\d{1,2}/\d{1,2}/art_\d+_\d+\.(?:shtml|html|htm)$", re.I),
    re.compile(r"/content/[0-9a-f]{8}-[0-9a-f-]{20,}\.(?:html|shtml|htm)$", re.I),
    re.compile(r"/20\d{4}/.+\.(?:shtml|html|htm)$", re.I),
]


@dataclass
class LinkItem:
    title: str
    url: str
    date_text: str = ""
    publish_date: object | None = None
    context: str = ""


@dataclass
class Article:
    title: str
    url: str
    publish_date: object | None
    text: str
    attachments: list[dict[str, str]]


def clean_text(text: str) -> str:
    text = str(text or "")
    # 清掉 Excel/Word XML 不允许的控制字符。
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
    text = re.sub(r"[\u00a0\u3000]+", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def same_site(url: str, base_url: str) -> bool:
    u = urlparse(url)
    b = urlparse(base_url)
    if not u.netloc or not b.netloc:
        return True
    un = u.netloc.lower().removeprefix("www.")
    bn = b.netloc.lower().removeprefix("www.")
    return un == bn or un.endswith("." + bn)


def normalize_url(href: str, base_url: str) -> str | None:
    if not href:
        return None
    href = href.strip()
    if any(href.lower().startswith(p) for p in BAD_LINK_PREFIXES):
        return None
    url = urljoin(base_url, href)
    url, _frag = urldefrag(url)
    if not url.startswith(("http://", "https://")):
        return None
    return url


def is_probably_article_url(url: str) -> bool:
    path = urlparse(url).path
    if not path or path == "/":
        return False
    if any(p.search(path) for p in ARTICLE_URL_PATTERNS):
        return True
    # 南通等站点的政务内容 URL 常带 uuid，但是不一定有日期。
    if "/content/" in path.lower() and path.lower().endswith((".html", ".htm", ".shtml")):
        return True
    if path.lower().endswith((".html", ".htm", ".shtml")) and re.search(r"20\d{2}", path):
        return True
    return False


def extract_links(html: str, base_url: str, only_same_site: bool = True) -> list[LinkItem]:
    soup = BeautifulSoup(html, "lxml")
    results: list[LinkItem] = []
    seen: set[str] = set()
    for a in soup.find_all("a"):
        href = a.get("href")
        url = normalize_url(href, base_url)
        if not url:
            continue
        if only_same_site and not same_site(url, base_url):
            continue
        if url in seen:
            continue
        title = clean_text(a.get("title") or a.get_text(" ", strip=True) or a.get("aria-label") or "")
        if not title or len(title) < 2:
            continue
        parent_text = clean_text(a.parent.get_text(" ", strip=True) if a.parent else title)
        date = parse_cn_date(parent_text + " " + title + " " + url)
        date_text = date.strftime("%Y-%m-%d") if date else ""
        results.append(LinkItem(title=title, url=url, publish_date=date, date_text=date_text, context=parent_text[:300]))
        seen.add(url)
    return results


def discover_channel_urls(html: str, base_url: str, max_channels: int = 12) -> list[str]:
    """从首页发现可能有用的栏目页。这里只发现栏目，详情页另行过滤。"""
    urls: list[str] = []
    for item in extract_links(html, base_url, only_same_site=True):
        combined = f"{item.title} {item.url} {item.context}"
        if any(k in combined for k in CHANNEL_KEYWORDS):
            urls.append(item.url)
    deduped = []
    seen = set()
    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
        if len(deduped) >= max_channels:
            break
    return deduped


def extract_article(html: str, url: str, fallback_title: str | None = None, source_name: str | None = None) -> Article:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    all_text = clean_text(soup.get_text("\n", strip=True))
    title = extract_title(soup, fallback_title=fallback_title, source_name=source_name)
    publish_date = extract_publish_date(soup, all_text, url)
    text = extract_main_text(soup)
    attachments = extract_attachments(soup, url)
    return Article(title=title, url=url, publish_date=publish_date, text=text, attachments=attachments)


def extract_title(soup: BeautifulSoup, fallback_title: str | None = None, source_name: str | None = None) -> str:
    candidates: list[str] = []

    # 政府网站常把真实标题放在 meta 里，优先于 <title>。
    meta_names = [
        "ArticleTitle",
        "article:title",
        "PubTitle",
        "ContentTitle",
        "Title",
        "title",
        "og:title",
        "twitter:title",
        "DCSext.Title",
    ]
    for name in meta_names:
        node = soup.find("meta", attrs={"name": name}) or soup.find("meta", attrs={"property": name})
        if node and node.get("content"):
            candidates.append(clean_title(node.get("content", "")))

    for selector in [
        "h1",
        ".article-title",
        ".article_title",
        ".title",
        "#title",
        ".content-title",
        ".xxgk-title",
        ".detail-title",
        ".main-title",
    ]:
        node = soup.select_one(selector)
        if node:
            candidates.append(clean_title(node.get_text(" ", strip=True)))

    if soup.title:
        candidates.append(clean_title(soup.title.get_text(" ", strip=True)))

    if fallback_title:
        candidates.append(clean_title(fallback_title))

    for t in candidates:
        if is_valid_title(t, source_name=source_name):
            return t

    # 如果页面标题都是网站名/跳转提示，则用列表页标题兜底。
    if fallback_title and clean_title(fallback_title):
        return clean_title(fallback_title)
    return "未提取到标题"


def clean_title(title: str) -> str:
    t = clean_text(title)
    # 去掉常见站点后缀，但不要把“——”副标题误删。
    t = re.sub(r"[\-_]\s*(?:中华人民共和国|江苏省|湖北省|黑龙江省|南通市).{0,20}(?:厅|局|部|委员会|政府).*$", "", t).strip()
    t = re.sub(r"\s+", " ", t)
    return t


def is_valid_title(title: str, source_name: str | None = None) -> bool:
    t = clean_text(title)
    if len(t) < 4:
        return False
    if source_name and t == source_name:
        return False
    if any(part == t or part in t for part in GENERIC_TITLE_PARTS):
        return False
    # 明显不是正文标题的页面提示。
    if "是否继续" in t or "链接即将离开" in t:
        return False
    return True


def extract_publish_date(soup: BeautifulSoup, all_text: str, url: str):
    # 优先匹配“发布时间/发布日期/时间/日期”附近的日期。
    patterns = [
        r"(?:发布时间|发布日期|发文日期|成文日期|更新时间|时间|日期)[:：\s]*([20]\d{3}[-/.年]\d{1,2}[-/.月]\d{1,2}日?)",
        r"([20]\d{3}[-/.年]\d{1,2}[-/.月]\d{1,2}日?)",
    ]
    head_text = all_text[:2500]
    for pat in patterns:
        m = re.search(pat, head_text)
        if m:
            dt = parse_cn_date(m.group(1))
            if dt:
                return dt
    return parse_cn_date(url)


def extract_main_text(soup: BeautifulSoup) -> str:
    selectors = [
        ".TRS_Editor",
        ".trs_editor",
        ".article-content",
        ".article_content",
        ".article",
        ".content",
        ".main-content",
        ".main",
        ".detail",
        "#zoom",
        "#article",
        "#content",
        "#main",
        "body",
    ]
    best = ""
    for selector in selectors:
        node = soup.select_one(selector)
        if not node:
            continue
        for bad in node.select("script, style, nav, header, footer, .nav, .footer, .header, .crumb, .breadcrumb"):
            bad.decompose()
        text = clean_text(node.get_text("\n", strip=True))
        # 排除页面导航/跳转页造成的大段无关内容。
        if "您访问的链接即将离开" in text[:200]:
            continue
        if len(text) > len(best):
            best = text
        if len(best) > 300:
            break
    return best


def extract_attachments(soup: BeautifulSoup, page_url: str) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    seen = set()
    for a in soup.find_all("a"):
        href = a.get("href")
        url = normalize_url(href, page_url)
        if not url or url in seen:
            continue
        path = urlparse(url).path.lower()
        ext = Path(path).suffix
        text = clean_text(a.get_text(" ", strip=True) or Path(path).name)
        if ext in ATTACHMENT_EXTS or ("附件" in text and is_probably_article_url(url) is False):
            attachments.append({"name": text or Path(path).name or "附件", "url": url})
            seen.add(url)
    return attachments


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？；;!?])\s*|\n+", text)
    return [clean_text(p) for p in parts if clean_text(p)]
