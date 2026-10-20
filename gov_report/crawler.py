from __future__ import annotations

import hashlib
import re
import traceback
from collections import deque
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .classifier import classify, contains_any, make_summary, extract_change_points
from .llm_classifier import LLMClassifier
from .date_utils import fmt_date, in_range
from .http import HttpClient, sanitize_filename
from .parser import (ATTACHMENT_EXTS, Article, LinkItem, discover_channel_urls, extract_article, extract_links,
                     extract_pagination_urls, is_probably_article_url, clean_text)


class GovCrawler:
    def __init__(
        self,
        sources: list[dict],
        keywords: dict[str, list[str]],
        output_dir: str | Path,
        max_channels_per_source: int = 0,
        max_detail_per_source: int = 0,
        download_attachments: bool = True,
        sleep: float = 0.5,
        verify_ssl: bool = True,
        strict: bool = True,
        save_rejected: bool = True,
        use_llm: bool = True,
        browser_fallback: bool = False,
        allow_rule_fallback: bool = False,
        progress_callback: Callable[[dict], None] | None = None,
    ) -> None:
        self.sources = sources
        self.keywords = keywords
        self.output_dir = Path(output_dir)
        self.attachments_dir = self.output_dir / "attachments"
        self.max_channels_per_source = max_channels_per_source
        self.max_detail_per_source = max_detail_per_source
        self.download_attachments = download_attachments
        self.client = HttpClient(sleep=sleep, verify_ssl=verify_ssl, browser_fallback=browser_fallback)
        self.strict = strict
        self.save_rejected = save_rejected
        self.logs: list[str] = []
        self.rejected: list[dict] = []
        self.llm = LLMClassifier(cache_path=self.output_dir / "llm_cache.jsonl", enabled=use_llm)
        self.allow_rule_fallback = allow_rule_fallback
        self.llm_used_count = 0
        self.llm_cache_hit_count = 0
        self.progress_callback = progress_callback

    def progress(self, event: str, **data) -> None:
        if self.progress_callback:
            self.progress_callback({"event": event, **data})

    def crawl(self, start, end, source_name: str | None = None) -> list[dict]:
        selected_sources = [s for s in self.sources if not source_name or s["name"] == source_name]
        if source_name and not selected_sources:
            raise ValueError(f"没有找到站点配置: {source_name}")

        all_records: list[dict] = []
        total = len(selected_sources)
        for idx, source in enumerate(selected_sources, 1):
            self.progress("source_started", source=source.get("name", ""), index=idx, total=total)
            self.log(f"\n[采集进度] {idx}/{total} {source.get('name', '')}")
            try:
                records = self.crawl_source(source, start, end)
                all_records.extend(records)
            except Exception as e:
                self.progress("error", source=source.get("name", ""), kind="source")
                self.log(f"[ERROR] {source.get('name')} 采集失败: {e}\n{traceback.format_exc()}")
            finally:
                self.client.close_browser()
                self.progress("source_finished", source=source.get("name", ""), index=idx, total=total)
        self.write_log()
        return dedupe_records(all_records)

    def crawl_source(self, source: dict, start, end) -> list[dict]:
        name = source["name"]
        base_url = source["base_url"]
        self.log(f"\n=== {name} ===")

        seeds = unique_keep_order([base_url] + list(source.get("list_urls") or []))
        pending = deque((url, False, normalize_url_for_dedupe(url)) for url in seeds)
        queued = {normalize_url_for_dedupe(url) for url in seeds}
        navigation_keys = set(queued)
        visited = set()
        page_fingerprints: dict[str, set[str]] = {}
        jcms_bridges = set()
        channel_names = dict(source.get("channel_names") or {})
        discovered = 0
        list_count = 0
        candidate_by_url: dict[str, LinkItem] = {}
        while pending:
            list_url, is_pagination, chain_key = pending.popleft()
            key = normalize_url_for_dedupe(list_url)
            if key in visited:
                continue
            visited.add(key)
            try:
                html, final_url = self.client.fetch_text(list_url)
                self.progress("page_processed", source=name, kind="list")
                final_key = normalize_url_for_dedupe(final_url)
                if final_key != key and final_key in visited:
                    continue
                visited.add(final_key)
                links = extract_links(html, final_url, only_same_site=True)
                # 把列表页URL写入候选上下文，便于判断“是否来自政策栏目”。
                for link in links:
                    link.context = f"{link.context} 栏目:{channel_names.get(list_url, '')} 列表页:{list_url} 最终列表页:{final_url}"
                    candidate_by_url.setdefault(normalize_url_for_dedupe(link.url), link)
                list_count += 1
                self.log(f"列表页 {list_url} 提取链接 {len(links)} 条")
                channels = discover_channel_urls(html, final_url, max_channels=0)
                navigation_keys.update(normalize_url_for_dedupe(url) for url in channels)
                for channel in channels:
                    channel_key = normalize_url_for_dedupe(channel)
                    if channel_key in queued or channel_key in visited:
                        continue
                    if self.max_channels_per_source > 0 and discovered >= self.max_channels_per_source:
                        break
                    queued.add(channel_key)
                    pending.append((channel, False, channel_key))
                    channel_names[channel] = next((x.title for x in links if x.url == channel), "")
                    discovered += 1
                    self.log(f"发现子栏目: {channel}")

                next_urls = extract_pagination_urls(html, final_url)
                navigation_keys.update(normalize_url_for_dedupe(url) for url in next_urls)
                content_urls = sorted({
                    x.url for x in links
                    if normalize_url_for_dedupe(x.url) not in navigation_keys
                    and self.should_fetch_candidate(x)
                })
                fingerprint = hashlib.sha256("\n".join(content_urls).encode()).hexdigest() if content_urls else ""
                fingerprints = page_fingerprints.setdefault(chain_key, set())
                repeated = bool(fingerprint and fingerprint in fingerprints)
                if fingerprint:
                    fingerprints.add(fingerprint)
                # JCMS may return the inline first group once before advancing to the next group.
                query = dict(parse_qsl(urlparse(final_url).query))
                first_group = query.get("startrecord") == "1" or query.get("page") == "1"
                bridge = repeated and first_group and chain_key not in jcms_bridges and urlparse(final_url).path == "/module/web/jpage/dataproxy.jsp"
                if bridge:
                    jcms_bridges.add(chain_key)
                if is_pagination and repeated and not bridge:
                    self.log(f"分页内容重复，停止继续翻页: {final_url}")
                    continue
                for next_url in next_urls:
                    next_key = normalize_url_for_dedupe(next_url)
                    if next_key not in queued and next_key not in visited:
                        queued.add(next_key)
                        pending.append((next_url, True, chain_key))
                        channel_names[next_url] = channel_names.get(list_url, "")
                        self.log(f"发现下一页: {next_url}")
            except Exception as e:
                self.progress("error", source=name, kind="list")
                self.log(f"列表页失败: {list_url} | {e}")

        self.log(f"栏目遍历完成：发现 {discovered} 个子栏目，读取 {list_count} 个列表/分页页面")

        candidates = list(candidate_by_url.values())
        records: list[dict] = []
        fetched = 0

        # 优先抓：已知日期在范围内且像详情页的链接。
        ranked = sorted(candidates, key=lambda x: (x.publish_date is None, x.date_text), reverse=False)
        for item in ranked:
            if self.max_detail_per_source > 0 and fetched >= self.max_detail_per_source:
                break
            if normalize_url_for_dedupe(item.url) in navigation_keys:
                continue

            if item.publish_date and not in_range(item.publish_date, start, end):
                continue

            if not self.should_fetch_candidate(item):
                self.reject(source, item, reason="不像详情文章链接或标题/上下文未命中")
                continue

            try:
                html, final_url = self.client.fetch_text(item.url)
                fetched += 1
                self.progress("page_processed", source=name, kind="detail")
                article = extract_article(html, final_url, fallback_title=item.title, source_name=name)
                pub_date = article.publish_date or item.publish_date
                if not in_range(pub_date, start, end):
                    self.reject(source, item, article=article, reason="发布时间不在统计区间")
                    continue

                # 如果详情页标题抽取失败/为站名，使用列表页标题兜底已在 parser 中完成。
                cls = classify(
                    article.title or item.title,
                    article.text,
                    self.keywords,
                    url=article.url,
                    source_name=name,
                    strict=self.strict,
                    context=item.context,
                )

                decision = self.decide_with_optional_llm(source, article, pub_date, cls)
                if not decision["include"]:
                    self.reject(source, item, article=article, reason=decision.get("reason", "分类规则/LLM未通过"))
                    continue

                record = self.article_to_record(source, article, pub_date, decision["cls"], llm_result=decision.get("llm_result"))
                records.append(record)
                self.progress("record_included", source=name)
                self.log(f"命中: {fmt_date(pub_date)} | {record['category']} | {record['title']} | {record['url']} | 判定:{record.get('decision_source','')}")
            except Exception as e:
                self.progress("error", source=name, kind="detail")
                self.log(f"详情页失败: {item.url} | {e}")

        self.log(f"{name} 命中 {len(records)} 条，详情抓取 {fetched} 条")
        return records

    def should_fetch_candidate(self, item: LinkItem) -> bool:
        if Path(urlparse(item.url).path).suffix.lower() in ATTACHMENT_EXTS:
            return False
        title_context = f"{item.title} {item.context} {item.url}"
        strong_title_hit = contains_any(
            title_context,
            self.keywords.get("personnel", [])
            + [
                "农药",
                "化工",
                "危险化学品",
                "危化品",
                "排污许可",
                "环境影响评价",
                "行政许可",
                "标准",
                "通知",
                "函",
                "决定",
                "意见",
                "公告",
                "公示",
                "通报",
                "批复",
                "政策解读",
                "申报",
                "征集",
                "印发",
                "转发",
                "政策",
                "政府信息公开",
                "政务公开",
            ],
        )
        # 有日期 + 像详情 URL，可以抓；无日期则必须标题/上下文命中强关键词且像详情 URL。
        if is_probably_article_url(item.url):
            return item.publish_date is not None or strong_title_hit
        # 少数站点详情URL没有典型特征，则必须有日期且标题强命中，避免首页/栏目页混入。
        return item.publish_date is not None and strong_title_hit

    def crawl_manual_urls(self, manual_urls: Iterable[str], start, end) -> list[dict]:
        records = []
        source = {"name": "手工补充链接", "region": "", "department": "", "base_url": ""}
        for url in manual_urls:
            try:
                html, final_url = self.client.fetch_text(url)
                self.progress("page_processed", source="手工补充链接", kind="detail")
                article = extract_article(html, final_url, fallback_title=None, source_name="")
                if not in_range(article.publish_date, start, end):
                    continue
                cls = classify(article.title, article.text, self.keywords, url=article.url, strict=self.strict, context="手工补充链接")
                decision = self.decide_with_optional_llm(source, article, article.publish_date, cls)
                if not decision["include"]:
                    continue
                records.append(self.article_to_record(source, article, article.publish_date, decision["cls"], llm_result=decision.get("llm_result")))
                self.progress("record_included", source="手工补充链接")
            except Exception as e:
                self.progress("error", source="手工补充链接", kind="detail")
                self.log(f"手工链接失败: {url} | {e}")
        self.client.close_browser()
        return dedupe_records(records)

    def decide_with_optional_llm(self, source: dict, article: Article, pub_date, cls: dict) -> dict:
        """规则高置信直接通过/排除；模糊候选交给 GPT-5.5 复判。"""
        bucket, reason = self.rule_bucket(article, cls)

        if bucket == "accept":
            cls = dict(cls)
            cls["decision_source"] = "规则硬通过"
            cls["rule_reason"] = reason
            return {"include": True, "cls": cls, "reason": reason}

        if bucket == "reject":
            return {"include": False, "cls": cls, "reason": reason}

        # 模糊候选：调用 GPT-5.5。默认不再“规则兜底通过”，避免半信半疑的内容进入报告。
        # 如确实需要旧行为，可在 main.py 中启用 --allow-rule-fallback。
        if not self.llm.is_available():
            if self.allow_rule_fallback and cls.get("is_relevant"):
                cls = dict(cls)
                cls["decision_source"] = "规则兜底命中（LLM未启用）"
                cls["rule_reason"] = reason
                return {"include": True, "cls": cls, "reason": reason}
            return {"include": False, "cls": cls, "reason": f"{reason}；LLM未启用，模糊候选默认不收录"}

        llm_input = {
            "title": article.title,
            "url": article.url,
            "source_name": source.get("name", ""),
            "region": source.get("region", ""),
            "department": source.get("department", ""),
            "publish_date": fmt_date(pub_date),
            "text": article.text,
            "attachments": article.attachments,
            "rule_info": {
                "bucket": bucket,
                "reason": reason,
                "categories": cls.get("categories", []),
                "formal_policy": cls.get("formal_policy"),
                "business_related": cls.get("business_related"),
                "in_policy_column": cls.get("in_policy_column"),
                "official_document_type": cls.get("official_document_type"),
                "news_like": cls.get("news_like"),
                "reject_reasons": cls.get("reject_reasons", []),
                "policy_hits": cls.get("policy_hits", []),
                "personnel_hits": cls.get("personnel_hits", []),
                "related_directions": cls.get("related_directions", []),
            },
        }
        llm_result = self.llm.classify_article(llm_input)
        self.llm_used_count += 1
        if llm_result.get("from_cache"):
            self.llm_cache_hit_count += 1

        if not llm_result.get("include"):
            return {
                "include": False,
                "cls": cls,
                "llm_result": llm_result,
                "reason": f"GPT复判排除：{llm_result.get('exclude_reason') or llm_result.get('reason')}",
            }

        new_cls = self.cls_from_llm(cls, llm_result)
        return {
            "include": True,
            "cls": new_cls,
            "llm_result": llm_result,
            "reason": llm_result.get("reason", "GPT复判通过"),
        }

    def rule_bucket(self, article: Article, cls: dict) -> tuple[str, str]:
        """返回 accept / reject / ambiguous。"""
        title = article.title or ""
        reject_reasons = cls.get("reject_reasons") or []

        # 标题明显错误、栏目页、跳转页：直接排除，不浪费模型。
        if any("标题为网站名/栏目名/跳转提示" in r for r in reject_reasons):
            return "reject", "标题为网站名/栏目名/跳转提示，直接排除"

        if cls.get("project_eia_like"):
            return "reject", "单个建设项目环评受理/拟审查/审批决定类公示，属于项目文件，不按政策文件收录"

        categories = cls.get("categories") or []
        formal_policy = bool(cls.get("formal_policy"))
        business_related = bool(cls.get("business_related"))
        news_like = bool(cls.get("news_like"))
        personnel_hits = cls.get("personnel_hits") or []
        policy_hits = cls.get("policy_hits") or []
        in_policy_column = bool(cls.get("in_policy_column"))
        official_document_type = cls.get("official_document_type") or ""

        # 规则高置信保留：正式任免/任前公示/人选公示。
        if "人事任免" in categories and not news_like:
            return "accept", "规则高置信：正式人事任免/任前公示/人选公示"

        # v5.2：用户新口径——只要属于政策栏目且是正式文种（通知/函/决定/公告/公示等），
        # 就确定算政策文件，不需要 GPT。
        if formal_policy and in_policy_column and official_document_type:
            return "accept", f"规则硬通过：政策栏目正式文种（{official_document_type}）"

        # 其它极少数硬白名单动作仍可直收。
        hard_direct_policy_terms = [
            "农药经营许可",
            "农药登记",
            "行政许可决定书",
            "行政许可",
            "排污许可证",
        ]
        if formal_policy and any(k in title for k in hard_direct_policy_terms):
            return "accept", "规则硬通过：行政许可/农药许可/排污许可证类事项"

        # 明显普通新闻/会议/视频/活动，且不是正式文件：直接排除。
        if news_like and not formal_policy:
            return "reject", "普通会议/调研/活动/视频/报道，且不像正式文件，直接排除"

        # 既不像正式文件，也没有企业相关性，也没有任免迹象：直接排除。
        if not formal_policy and not business_related and not personnel_hits and not policy_hits:
            return "reject", "无正式政策/企业相关/任免信号，直接排除"

        # 像正式文件但相关性不足，或者相关但不像正式文件，交给 GPT 判断。
        return "ambiguous", "规则判断为模糊候选，交给 GPT-5.5 复判"

    def cls_from_llm(self, rule_cls: dict, llm_result: dict) -> dict:
        categories = []
        if llm_result.get("is_personnel"):
            categories.append("人事任免")
        if llm_result.get("is_policy"):
            categories.append("政策文件")
        if not categories and llm_result.get("include"):
            if llm_result.get("final_category") == "personnel":
                categories.append("人事任免")
            else:
                categories.append("政策文件")

        return {
            **rule_cls,
            "is_relevant": bool(llm_result.get("include")),
            "categories": categories,
            "related_directions": llm_result.get("related_directions") or rule_cls.get("related_directions") or [],
            "decision_source": "GPT-5.5复判",
            "policy_subtype": llm_result.get("policy_subtype", ""),
            "document_action": llm_result.get("document_action", ""),
            "llm_reason": llm_result.get("reason", ""),
            "llm_confidence": llm_result.get("confidence", 0),
            "llm_summary": llm_result.get("summary", ""),
            "llm_change_points": llm_result.get("change_points", []),
        }

    def article_to_record(self, source: dict, article: Article, pub_date, cls: dict, llm_result: dict | None = None) -> dict:
        title = article.title
        summary = cls.get("llm_summary") or make_summary(title, article.text, self.keywords)
        change_points = cls.get("llm_change_points") or extract_change_points(article.text, self.keywords)
        attachment_infos = []
        if article.attachments:
            article_attach_dir = self.attachments_dir / sanitize_filename(title[:50])
            for att in article.attachments:
                local_path = ""
                if self.download_attachments:
                    downloaded = self.client.download(att["url"], article_attach_dir, filename_hint=att.get("name") or "attachment")
                    if downloaded:
                        local_path = str(downloaded.relative_to(self.output_dir))
                attachment_infos.append({"name": att.get("name", "附件"), "url": att.get("url", ""), "local_path": local_path})

        text_hash = hashlib.sha1(clean_text(article.text[:5000]).encode("utf-8", errors="ignore")).hexdigest()
        return {
            "title": title,
            "url": article.url,
            "normalized_url": normalize_url_for_dedupe(article.url),
            "source_name": source.get("name", ""),
            "region": source.get("region", ""),
            "department": source.get("department", ""),
            "publish_date": fmt_date(pub_date),
            "category": "、".join(cls.get("categories") or []),
            "related_directions": "、".join(cls.get("related_directions") or []),
            "summary": summary,
            "change_points": "\n".join(change_points),
            "personnel_hits": "、".join(cls.get("personnel_hits") or []),
            "policy_hits": "、".join(cls.get("policy_hits") or []),
            "change_hits": "、".join(cls.get("change_hits") or []),
            "content_hash": text_hash,
            "attachments": attachment_infos,
            "decision_source": cls.get("decision_source", "规则命中"),
            "rule_reason": cls.get("rule_reason", ""),
            "policy_subtype": cls.get("policy_subtype", ""),
            "document_action": cls.get("document_action", ""),
            "in_policy_column": cls.get("in_policy_column", ""),
            "official_document_type": cls.get("official_document_type", ""),
            "llm_reason": cls.get("llm_reason", ""),
            "llm_confidence": cls.get("llm_confidence", ""),
            "llm_used": bool(llm_result),
            "llm_from_cache": bool((llm_result or {}).get("from_cache")),
        }

    def reject(self, source: dict, item: LinkItem, reason: str, article: Article | None = None) -> None:
        if not self.save_rejected:
            return
        self.rejected.append(
            {
                "source_name": source.get("name", ""),
                "candidate_title": item.title,
                "article_title": article.title if article else "",
                "url": article.url if article else item.url,
                "date": fmt_date(article.publish_date if article else item.publish_date),
                "reason": reason,
            }
        )

    def log(self, message: str) -> None:
        print(message, flush=True)
        self.logs.append(message)

    def write_log(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logs.append(f"LLM调用候选数：{self.llm_used_count}，其中缓存命中：{self.llm_cache_hit_count}")
        (self.output_dir / "crawl_log.txt").write_text("\n".join(self.logs), encoding="utf-8")
        if self.save_rejected and self.rejected:
            import json

            (self.output_dir / "rejected_candidates.json").write_text(
                json.dumps(self.rejected, ensure_ascii=False, indent=2), encoding="utf-8"
            )


def unique_keep_order(items: Iterable[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def dedupe_links(items: Iterable[LinkItem]) -> list[LinkItem]:
    seen = set()
    out = []
    for item in items:
        key = normalize_url_for_dedupe(item.url)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def dedupe_records(records: Iterable[dict]) -> list[dict]:
    seen = set()
    out = []
    for r in records:
        title_key = normalize_title(r.get("title", ""))
        keys = [
            ("url", r.get("normalized_url") or normalize_url_for_dedupe(r.get("url", ""))),
            ("title", r.get("source_name", ""), r.get("publish_date", ""), title_key),
        ]
        if r.get("content_hash"):
            keys.append(("hash", r.get("source_name", ""), r.get("publish_date", ""), r.get("content_hash")))
        if any(k in seen for k in keys):
            continue
        for k in keys:
            seen.add(k)
        out.append(r)
    return out


def normalize_url_for_dedupe(url: str) -> str:
    if not url:
        return ""
    p = urlparse(url.strip())
    scheme = ""  # 去掉 http/https 差异
    netloc = p.netloc.lower().removeprefix("www.")
    path = re.sub(r"/{2,}", "/", p.path or "/")
    path = re.sub(r"/(index|default)\.(html|htm|shtml|shtm)$", "/", path, flags=re.I)
    path = path.rstrip("/") or "/"
    # 保留必要查询，去掉追踪参数。
    qs = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith(("utm_", "from"))]
    query = urlencode(qs)
    return urlunparse((scheme, netloc, path, "", query, ""))


def normalize_title(title: str) -> str:
    title = clean_text(title)
    title = re.sub(r"[\s\u3000]+", "", title)
    title = re.sub(r"[【】\[\]（）()《》“”‘’、，。；：:|｜_-]", "", title)
    return title[:80]


def read_manual_urls(path: str | Path) -> list[str]:
    path = Path(path)
    if not path.exists():
        return []
    urls = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls
