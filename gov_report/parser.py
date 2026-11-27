from __future__ import annotations

import ast
import json
import re
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag, urlencode, parse_qsl

from bs4 import BeautifulSoup
from lxml import etree

from .date_utils import parse_cn_date

ATTACHMENT_EXTS = {
    ".ofd",
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


def is_attachment_url(url: str) -> bool:
    parsed = urlparse(url)
    if Path(parsed.path).suffix.lower() in ATTACHMENT_EXTS:
        return True
    if parsed.path.lower().endswith('/attachmentcontroller/download.do'):
        return True
    if parsed.path.lower().rstrip('/') == '/zxfile/reader':
        return any(key.lower() == 'file' and Path(urlparse(value).path).suffix.lower() in ATTACHMENT_EXTS
                   for key, value in parse_qsl(parsed.query))
    return False

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
    "公开",
    "目录",
    "规章",
    "标准",
    "规划",
    "计划",
    "权责",
    "行政执法",
    "意见征集",
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
    date_reliable: bool = False
    pinned: bool = False
    in_navigation: bool = False
    list_date_conflict: bool = False
    list_dates: tuple[str, ...] = ()


@dataclass
class Article:
    title: str
    url: str
    publish_date: object | None
    text: str
    attachments: list[dict[str, str]]
    date_source: str = ""
    date_evidence: list[dict[str, str]] = field(default_factory=list)


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
    if re.search(r"/(?:index(?:_\d+)?|h5(?:_\d+)?|list(?:_\d+)?|default|public_[^/]*|zfxxgk|redirect_firstChannel)\.(?:s?html?|jsp)$", path, re.I):
        return False
    if any(p.search(path) for p in ARTICLE_URL_PATTERNS):
        return True
    # 南通等站点的政务内容 URL 常带 uuid，但是不一定有日期。
    if "/content/" in path.lower() and path.lower().endswith((".html", ".htm", ".shtml")):
        return True
    if path.lower().endswith((".html", ".htm", ".shtml")) and re.search(r"20\d{2}", path):
        return True
    return False


def script_written_html(script: str) -> str:
    fragments = []
    pattern = r"document\.write(?:ln)?\s*\(\s*('(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")\s*\)"
    for match in re.finditer(pattern, script, re.S):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                value = ast.literal_eval(match.group(1).replace(r"\/", "/"))
        except (SyntaxError, ValueError):
            continue
        if isinstance(value, str):
            fragments.append(value)
    return "\n".join(fragments)


def navigation_soup(html: str) -> BeautifulSoup:
    """Expose links stored in JCMS XML and literal document.write fragments."""
    soup = BeautifulSoup(html, "lxml")
    fragments = []
    xml_documents = []
    if html.lstrip().startswith(("<datastore", "<?xml")):
        xml_documents.append(html)
    for script in soup.find_all("script"):
        content = script.string or ""
        if script.get("type", "").lower() == "text/xml" and "<datastore" in content:
            xml_documents.append(content)
        else:
            fragments.append(script_written_html(content))
    for content in xml_documents:
        document = etree.fromstring(content.encode("utf-8"), etree.XMLParser(
            resolve_entities=False, no_network=True, recover=True,
        ))
        if document is None:
            continue
        for record in document.iter("record"):
            fragments.append("".join(record.itertext()))
        for group in document.iter("nextgroup"):
            fragment = BeautifulSoup("".join(group.itertext()), "lxml")
            for anchor in fragment.find_all("a", href=True):
                anchor["data-pagination"] = "next"
                fragments.append(str(anchor))
    for fragment in fragments:
        if fragment:
            container = soup.new_tag("div", attrs={"data-extracted-markup": "true"})
            parsed = BeautifulSoup(fragment, "lxml")
            for node in list((parsed.body or parsed).contents):
                container.append(node.extract())
            (soup.body or soup).append(container)
    return soup


def extract_static_script_urls(html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    urls = []
    for script in soup.find_all("script", src=True):
        url = normalize_url(script["src"], base_url)
        if url and same_site(url, base_url) and re.search(
            r"/script/\d+/[^/]+\.js|/(?:header|head|nav|footer|top|bottom|menu)[^/]*\.js$|/cms_files/filemanager/(?:[^/]+/)?script/", urlparse(url).path, re.I,
        ):
            urls.append(url)
    return list(dict.fromkeys(urls))


def extract_redirect_url(html: str, base_url: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for meta in soup.find_all("meta"):
        if meta.get("http-equiv", "").lower() == "refresh":
            match = re.search(r"url\s*=\s*['\"]?([^'\"]+)", meta.get("content", ""), re.I)
            if match:
                target = normalize_url(match.group(1).strip(), base_url)
                if target and same_site(target, base_url):
                    return target
    if soup.find("a", href=True):
        return None
    for script in soup.find_all("script"):
        for match in re.finditer(r"(?:window\.)?location(?:\.href|\.replace\s*\()?\s*(?:=\s*)?['\"]([^'\"]+)['\"]", script.string or ""):
            target = normalize_url(match.group(1), base_url)
            if target and urlparse(target).hostname == urlparse(base_url).hostname and target != base_url:
                return target
    return None


def extract_links(html: str, base_url: str, only_same_site: bool = True, *, _soup: BeautifulSoup | None = None) -> list[LinkItem]:
    soup = _soup if _soup is not None else navigation_soup(html)
    results: list[LinkItem] = []
    seen: set[str] = set()
    for a in soup.select("a, area[href], [onclick], select option[value]"):
        href = a.get("href")
        if a.name == "option":
            value = a.get("value", "")
            if not value.startswith(("http://", "https://", "/", "./", "../")):
                continue
            href = value
        if (not href or str(href).lower().startswith("javascript:")) and urlparse(base_url).hostname and urlparse(base_url).hostname.endswith("hlj.gov.cn"):
            channel_id = a.get("data-channelid", "")
            if re.fullmatch(r"[a-fA-F0-9]{32}", channel_id):
                href = f"/common/search/{channel_id}?" + urlencode({
                    "_isAgg": "true", "_isJson": "true", "_pageSize": 15,
                    "_template": "index", "page": 1,
                })
        if not href or str(href).lower().startswith(("javascript:", "#")):
            match = re.search(r"(?:window\.open\s*\(|(?:window\.)?location\.href\s*=\s*)['\"]([^'\"]+)['\"]", a.get("onclick", ""))
            if match:
                href = match.group(1)
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
        row = a.find_parent(["li", "tr", "dd"]) or a.parent or a
        parent_text = clean_text(row.get_text(" ", strip=True))
        date_nodes = []
        for node in row.select("time, span, em, font"):
            raw = node.get("datetime") or node.get_text(" ", strip=True)
            if re.fullmatch(r"(?:发布时间|发布日期|日期)?[:：\s]*20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?"
                            r"(?:[T\s]\d{1,2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?", raw):
                parsed = parse_cn_date(raw)
                if parsed:
                    date_nodes.append((node, parsed, raw))
        date = date_nodes[0][1] if date_nodes else explicit_day(parent_text + " " + title + " " + url)
        for node, _, raw in date_nodes:
            if node.find_parent("a") is a:
                title = re.sub(r"\s*" + re.escape(raw) + r"$", "", title).strip()
        visible_date = parse_cn_date(parent_text.replace(title, "", 1))
        date_text_only = parent_text.replace(title, "", 1)
        single_link = len({node.get("href") for node in row.select("a[href]")}) <= 1
        reliable = bool(single_link and ((date_nodes and len({node[1] for node in date_nodes}) == 1)
                        or (visible_date and date and visible_date == date
                            and re.search(r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}", date_text_only))))
        classes = " ".join(row.get("class", []))
        pinned = bool(re.search(r"(?:^|[\s_-])(?:top|pinned|zhiding)(?:$|[\s_-])", classes, re.I)
                      or row.get("data-top") in {"true", "1"} or "置顶" in parent_text)
        navigation = (a.find_parent(["nav", "header", "footer"]) is not None or
                      a.find_parent(attrs={"role": "navigation"}) is not None or
                      a.find_parent(class_=re.compile(r"^(?:nav|navbar|breadcrumb|footer|site-menu)$", re.I)) is not None)
        date_text = date.strftime("%Y-%m-%d") if date else ""
        results.append(LinkItem(title=title, url=url, publish_date=date, date_text=date_text,
                                context=parent_text[:300], date_reliable=reliable, pinned=pinned,
                                in_navigation=navigation))
        seen.add(url)
        if a.get("data-channelid") and a.get("data-code") and a.parent and a.parent.select_one("i.plus, i.icon, ol"):
            website = soup.find(id="websiteCode") or soup.find("meta", attrs={"name": "websiteCode"})
            website_code = (website.get("content") or website.get_text(strip=True)) if website else ""
            if website_code and urlparse(base_url).hostname and urlparse(base_url).hostname.endswith("hlj.gov.cn"):
                tree_url = urljoin(base_url, "/common/getChannelList") + "?" + urlencode({
                    "channelCode": a["data-code"], "websiteCodeName": website_code,
                })
                if tree_url not in seen:
                    results.append(LinkItem(title=title + "子栏目", url=tree_url, context=parent_text[:300]))
                    seen.add(tree_url)
    return results


def discover_channel_urls(html: str, base_url: str, max_channels: int = 12, *, _links=None) -> list[str]:
    """从首页发现可能有用的栏目页。这里只发现栏目，详情页另行过滤。"""
    urls: list[str] = []
    for item in (_links if _links is not None else extract_links(html, base_url, only_same_site=True)):
        if is_probably_article_url(item.url) or is_attachment_url(item.url) or has_document_headline(item):
            continue
        combined = f"{item.title} {item.url}"
        if any(k in combined for k in CHANNEL_KEYWORDS):
            urls.append(item.url)
    deduped = []
    seen = set()
    for url in urls:
        if url not in seen:
            deduped.append(url)
            seen.add(url)
        if max_channels > 0 and len(deduped) >= max_channels:
            break
    return deduped


def has_document_headline(item: LinkItem) -> bool:
    # Distinguish an actual notice from a channel called simply "通知公告".
    return not item.in_navigation and bool(re.search(
        r"关于.{3,}(?:通知|意见|决定|公告|批复|公示)|(?:任前公示|职务任免).{2,}|〔20\d{2}〕\s*\d+号", item.title))


def extract_pagination_urls(html: str, base_url: str, *, _soup: BeautifulSoup | None = None) -> list[str]:
    soup = _soup if _soup is not None else navigation_soup(html)
    urls = []
    for pager in soup.select(".pagination[uniturl][querydata][pageno][rows][count]"):
        target = normalize_url(pager["uniturl"], base_url)
        if not target or not same_site(target, base_url) or urlparse(target).path != "/api-gateway/jpaas-publish-server/front/page/build/unit":
            continue
        try:
            params = ast.literal_eval(pager["querydata"])
            current, size, total = int(pager["pageno"]), int(pager["rows"]), int(pager["count"])
            if not isinstance(params, dict) or not all(isinstance(k, str) and isinstance(v, (str, int)) for k, v in params.items()):
                continue
        except (ValueError, SyntaxError, TypeError):
            continue
        if current >= 1 and size > 0 and current * size < total:
            params["paramJson"] = json.dumps({"pageNo": current + 1, "pageSize": str(size)}, separators=(",", ":"))
            urls.append(target + "?" + urlencode(params))
    for anchor in soup.find_all("a", href=True):
        label = clean_text(anchor.get_text(" ", strip=True))
        next_page = anchor.get("data-pagination") == "next" or "next" in anchor.get("rel", [])
        next_page = next_page or bool(re.fullmatch(r"下一页|下页|next|[>»]+", label, re.I))
        if not next_page or anchor.get("aria-disabled") == "true":
            continue
        target = normalize_url(anchor["href"], base_url)
        if target and same_site(target, base_url) and target != base_url:
            urls.append(target)
    # TRS emits only JavaScript pagination controls in its static list pages.
    for match in re.finditer(r"createPageHTML\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*['\"](s?html?|htm)['\"]", html, re.I):
        total, current = int(match[1]), int(match[2])
        if current + 1 < total:
            target = normalize_url(f"{match[3]}_{current + 1}.{match[4]}", base_url)
            if target and same_site(target, base_url):
                urls.append(target)
    for script in soup.find_all("script"):
        code = script.string or ""
        current = re.search(r"\bvar\s+currentPage\s*=\s*(\d+)", code)
        total = re.search(r"\bvar\s+countPage\s*=\s*(\d+)", code)
        extension = re.search(r"index\.(s?html?)\b", code, re.I)
        if current and total and extension and "nextPage" in code and int(current[1]) + 1 < int(total[1]):
            target = normalize_url(f"index_{int(current[1]) + 1}.{extension[1]}", base_url)
            if target and same_site(target, base_url):
                urls.append(target)
    # TrueCMS already embeds the first group of records; request only the next group.
    for match in re.finditer(r"\.jpage\s*\(\s*\{(.*?)\}\s*\)", html, re.S):
        config = match[1]
        proxy = re.search(r"proxyUrl\s*:\s*['\"]([^'\"]+)['\"]", config)
        column = re.search(r"columnId\s*:\s*['\"]([a-fA-F0-9-]{36})['\"]", config)
        total = re.search(r"totalRecord\s*:\s*(\d+)", config)
        size = re.search(r"perPage\s*:\s*(\d+)", config)
        if not all((proxy, column, total, size)):
            continue
        target = normalize_url(proxy[1], base_url)
        if not target or not same_site(target, base_url) or urlparse(target).path != "/truecms/messageController/getMessage.do":
            continue
        page_size = max(1, int(size[1]))
        loaded = len(soup.select("#initData > ul, #initData > li, #initData > tr")) or page_size
        if loaded < int(total[1]):
            params = {"columnId": column[1], "startrecord": loaded + 1,
                      "endrecord": min(loaded + page_size, int(total[1])), "perpage": page_size,
                      "contentTemplate": "", "callback": "govreport"}
            urls.append(target + "?" + urlencode(params))
    if urlparse(base_url).hostname and urlparse(base_url).hostname.endswith("hlj.gov.cn") and soup.find(id="page_div"):
        channel = soup.find("meta", attrs={"name": "channelId"}) or soup.find("meta", id="channelId")
        page_size = soup.find("input", id="pageSize")
        channel_id = channel.get("content", "") if channel else ""
        if re.fullmatch(r"[a-fA-F0-9]{32}", channel_id):
            params = {"_isAgg": "true", "_isJson": "true", "_pageSize": int(page_size.get("value", 15)) if page_size else 15,
                      "_template": "index", "page": 2}
            urls.append(urljoin(base_url, f"/common/search/{channel_id}?{urlencode(params)}"))
    return list(dict.fromkeys(urls))


def extract_article(html: str, url: str, fallback_title: str | None = None, source_name: str | None = None) -> Article:
    soup = BeautifulSoup(html, "lxml")

    for tag in soup(["script", "style", "noscript", "iframe"]):
        tag.decompose()

    all_text = clean_text(soup.get_text("\n", strip=True))
    title = extract_title(soup, fallback_title=fallback_title, source_name=source_name)
    evidence = collect_date_evidence(soup, title, fallback_title)
    publish_date, date_source = publication_evidence(soup, all_text, url, evidence)
    text = extract_main_text(soup)
    attachments = extract_attachments(soup, url)
    return Article(title, url, publish_date, text, attachments, date_source, evidence)


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
    t = re.split(r"<meta\b", t, maxsplit=1, flags=re.I)[0]
    t = re.sub(r"<br\s*/?>", " ", t, flags=re.I)
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
    return publication_evidence(soup, all_text, url)[0]


DATE_NAMES = {"pubdate", "publishdate", "articletime", "articlepubdate", "articlepublishtime",
                  "article:published_time", "dcext.pubdate", "dcsext.pubdate", "dc.date", "pubtime", "datepublished"}
DAY = r"20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}(?!\d)日?"
FULL_DAY = re.compile(rf"(?<!\d)(?:{DAY}|20\d{{6}}(?!\d))")


def explicit_day(raw):
    # A year-only directory such as /xxgk2018/ is not January 1st, 2018.
    return next((d for m in FULL_DAY.finditer(raw) if (d := parse_cn_date(m[0]))), None)


def collect_date_evidence(soup, title, fallback_title=None):
    """Keep visible citations separate from CMS metadata, document dates and deadlines."""
    result = []
    def add(kind, raw, quote):
        dt = parse_cn_date(raw)
        if dt:
            row = dict(kind=kind, date=dt.date().isoformat(), quote=" ".join(quote.split())[:180])
            if row not in result:
                result.append(row)
    lines = (soup.body or soup).get_text("\n", strip=True).splitlines()
    heading = soup.find("h1")
    titles = {clean_title(v) for v in (title, fallback_title, heading.get_text(" ",strip=True) if heading else "")
              if v and is_valid_title(v) and len(v)<=250}
    for i, line in enumerate(lines):
        if len(line)>300 or clean_title(line) not in titles:
            continue
        after = " ".join(lines[i+1:i+12])[:300]
        header = (re.match(rf"(?:(?:发布日期|发布时间|日期|时间)\s*[:：]\s*)?({DAY})(?:\s+\d{{1,2}}:\d{{2}}(?::\d{{2}})?)?\s*(?:信息来源|文章来源|来源)\s*[:：]", after)
                  or re.match(rf"(?:发布日期|发布时间)\s*[:：]\s*({DAY})",after))
        if header:
            add("标题栏发布日期",header[1],after[:header.end()+24])
            break
    for meta in soup.find_all("meta"):
        if len(result)>=6:
            break
        key = meta.get("name") or meta.get("property") or ""
        value = meta.get("content", "")
        if key.lower() in DATE_NAMES and (dt := explicit_day(value)):
            add("发布元数据",dt.date().isoformat(),key+": "+value)
    # Only bounded article snippets go to the model; never send page HTML or credentials.
    main = soup.select_one("article, .TRS_Editor, .article-content, #zoom, main") or soup.body or soup
    text = " ".join(main.stripped_strings)[:3500]
    for m in re.finditer(DAY,text):
        if len(result)>=12:
            break
        prefix=re.split(r"[。；！？]",text[max(0,m.start()-42):m.start()])[-1]
        suffix=re.split(r"[。；！？]",text[m.end():m.end()+26])[0]
        kind = ("期限线索" if re.search(r"截止|截至|反馈期限|生效日期|实施日期|施行日期",prefix[-12:]) or re.match(r"\s*(?:日?前|之前|起施行|起实施|起生效)",suffix)
                else "发文日期" if re.search(r"(?:成文|发文)日期\s*[:：]?\s*$",prefix)
                else "更新日期" if re.search(r"更新(?:时间|日期)\s*[:：]?\s*$",prefix)
                else "正文日期线索")
        add(kind,m[0],prefix+m[0]+suffix)
    return result


def publication_evidence(soup: BeautifulSoup, all_text: str, url: str, evidence=None):
    if evidence is None:
        evidence = collect_date_evidence(soup, extract_title(soup))
    for row in evidence:
        if row["kind"]=="标题栏发布日期":
            return parse_cn_date(row["date"]),row["kind"]
    for meta in soup.find_all("meta"):
        if (meta.get("name") or meta.get("property") or "").lower() in DATE_NAMES:
            published = explicit_day(meta.get("content", ""))
            if published:
                return published, "发布元数据"
    # 优先匹配“发布时间/发布日期/时间/日期”附近的日期。
    patterns = [
        ("发布日期", r"(?:发布时间|发布日期|发布时间戳|发布于)"),
        ("发文日期", r"(?:发文日期|成文日期)"),
        ("更新日期", r"(?:更新时间|更新日期)"),
        ("页面日期线索", ""),
    ]
    head_text = all_text[:2500]
    for label, pat in patterns:
        m = re.search(pat + r"[:：\s]*(20\d{2}[-/.年]\d{1,2}[-/.月]\d{1,2}日?)", head_text)
        if m:
            dt = parse_cn_date(m.group(1))
            if dt:
                return dt, label
    return explicit_day(url), "网址日期线索"


def extract_main_text(soup: BeautifulSoup) -> str:
    selectors = [
        "article",
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
        if best and (selector in {"article", ".TRS_Editor", ".trs_editor", ".article-content", ".article_content", "#article"} or len(best) > 300):
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
        text = clean_text(a.get_text(" ", strip=True) or Path(path).name)
        if is_attachment_url(url) or ("附件" in text and is_probably_article_url(url) is False):
            attachments.append({"name": text or Path(path).name or "附件", "url": url})
            seen.add(url)
    return attachments


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[。！？；;!?])\s*|\n+", text)
    return [clean_text(p) for p in parts if clean_text(p)]
