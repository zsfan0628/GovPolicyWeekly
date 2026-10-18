from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

from .llm_config import (
    ENABLE_LLM_CACHE,
    LLM_MAX_BODY_CHARS,
    OPENAI_API_KEY,
    OPENAI_API_STYLE,
    OPENAI_BASE_URL,
    OPENAI_MAX_RETRIES,
    OPENAI_MODEL,
    OPENAI_TEMPERATURE,
    OPENAI_TIMEOUT_SECONDS,
)
from .parser import clean_text


SYSTEM_PROMPT = """你是政府网站政策信息筛选专家。你的任务是判断网页是否应进入《农药化工企业政策与人事任免周报》。

核心判断原则：
网页本身必须是在“发布、修订/重修、公开征求、政策解读、公告/公示、审批/许可、名单公示、人事任免”某个正式事项。
如果网页只是新闻报道、工作动态、会议活动，正文中只是“引用、依据、提到、学习、贯彻”某个政策文件或标准，不等于该网页在发布政策文件，必须排除。

只允许保留两类内容：

A. 人事任免：
只保留正式人事任免、干部任免、任免通知、任前公示、人选公示、任职/免职决定。
普通领导参加会议、主持会议、调研、讲话、理论学习、支委会、专题培训，不属于人事任免。

B. 与农药化工企业发展相关的政策文件：
只保留正式通知、公告、公示、通报、批复、决定、办法、规定、方案、指南、目录、标准、行政许可、审批决定、项目申报、资金补贴、政策解读、征求意见、名单公示等。
并且内容必须与以下至少一类企业发展事项有明确关系：
农药、农资、植保、化工、石油化工、精细化工、危险化学品、危化品、重大危险源、企业安全生产、生产经营单位、有限空间、排污许可、环评审批、环境影响评价、危废/固废/VOCs、污染防治、生态工业园区、工业企业、技术改造、智能制造、绿色工厂、专精特新、中小企业、专项资金、财政补贴、项目申报、标准制修订。

必须排除：
1. 普通会议新闻、领导调研、会见、活动报道、媒体报道、视频、海报、警示片、比赛、宣讲、党建理论学习、国际交流、灾害救助新闻、纯工作动态、首页、栏目页、跳转提示页。
2. 只是提到政府文件/标准/政策名称，但网页主旨是会议、宣传、活动、项目进展、工程建设、经验报道的内容。
3. 只是“根据/依据/按照/贯彻/落实某文件要求”开展工作，而不是发布、修订、征求、解读该文件。
4. “安全生产月”“宣贯培训”“警示教育”“专项活动安排”等宣传活动类通知，除非它直接设置新的企业法定义务、许可审批、项目申报或资金补贴，否则排除。
5. 与农药化工企业发展没有直接关系的泛化标准化、委员征集、救灾物资、普通安全生产新闻、普通污水厂升级报道、宏观经济新闻。
6. 单个建设项目环境影响评价文件受理情况公示、拟审查公示、审批决定公告、环评报告书/报告表附件等，属于项目文件或项目审批流程信息，不属于本周报要收集的政策文件。

include=true 必须同时满足：
- document_action 不是“仅引用/提及文件”、不是“普通新闻/活动”、不是“项目环评/项目公示”、不是“其他”；
- is_policy 或 is_personnel 至少一个为 true；
- 如果是政策文件，必须对农药化工企业或相关工业企业有明确影响。

输出要求：
- 你必须只输出 JSON，不要输出 Markdown，不要输出解释性正文。
- reason 要说明为什么保留或排除。
- summary 要短，只写与政策/任免直接相关的内容。
- change_points 只提取新增、修订、调整、延续、废止、申报、补贴、许可、审批、标准制修订等变化点。
"""

JSON_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "include": {"type": "boolean"},
        "final_category": {
            "type": "string",
            "enum": ["policy", "personnel", "policy_and_personnel", "exclude"],
        },
        "policy_subtype": {
            "type": "string",
            "enum": [
                "none",
                "通知",
                "公告",
                "公示",
                "通报",
                "批复",
                "决定",
                "办法规定",
                "方案指南",
                "目录标准",
                "行政许可",
                "审批决定",
                "项目申报",
                "资金补贴",
                "政策解读",
                "征求意见",
                "名单公示",
                "其他政策文件",
            ],
        },
        "document_action": {
            "type": "string",
            "enum": [
                "发布新文件",
                "修订/重修文件",
                "公开征求意见",
                "政策解读",
                "行政许可/审批",
                "名单/结果公示",
                "人事任免",
                "仅引用/提及文件",
                "普通新闻/活动",
                "项目环评/项目公示",
                "其他",
            ],
        },
        "is_personnel": {"type": "boolean"},
        "is_policy": {"type": "boolean"},
        "relevance_to_pesticide_chemical_enterprise": {
            "type": "string",
            "enum": ["high", "medium", "low", "none"],
        },
        "related_directions": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "农药/农资",
                    "化工/危化品",
                    "生态环境/排污",
                    "安全生产",
                    "产业扶持/项目申报",
                    "工信/技改",
                    "财政/资金",
                    "人事任免",
                ],
            },
        },
        "reason": {"type": "string"},
        "summary": {"type": "string"},
        "change_points": {"type": "array", "items": {"type": "string"}},
        "exclude_reason": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": [
        "include",
        "final_category",
        "policy_subtype",
        "document_action",
        "is_personnel",
        "is_policy",
        "relevance_to_pesticide_chemical_enterprise",
        "related_directions",
        "reason",
        "summary",
        "change_points",
        "exclude_reason",
        "confidence",
    ],
}


class LLMClassifier:
    def __init__(self, cache_path: str | Path | None = None, enabled: bool = True) -> None:
        self.enabled = enabled
        self.cache_path = Path(cache_path) if cache_path else None
        self.cache: dict[str, dict[str, Any]] = {}
        if self.cache_path and ENABLE_LLM_CACHE:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._load_cache()

    def is_available(self) -> bool:
        return bool(self.enabled and OPENAI_API_KEY and OPENAI_API_KEY != "请在这里填写你的API_KEY")

    def classify_article(self, item: dict[str, Any]) -> dict[str, Any]:
        """对单篇文章调用 GPT-5.5 复判。"""
        if not self.is_available():
            return self._fallback_result("LLM未启用或API_KEY未填写")

        payload_text = self._build_user_prompt(item)
        cache_key = self._cache_key(item, payload_text)
        if ENABLE_LLM_CACHE and cache_key in self.cache:
            result = dict(self.cache[cache_key])
            result["from_cache"] = True
            return result

        last_error = ""
        for attempt in range(1, OPENAI_MAX_RETRIES + 1):
            try:
                if OPENAI_API_STYLE == "responses":
                    result = self._call_responses_api(payload_text)
                else:
                    result = self._call_chat_completions_api(payload_text)
                result = self._normalize_result(result)
                result["from_cache"] = False
                if ENABLE_LLM_CACHE:
                    self.cache[cache_key] = result
                    self._append_cache(cache_key, result)
                return result
            except Exception as e:
                last_error = str(e)
                if attempt < OPENAI_MAX_RETRIES:
                    time.sleep(1.5 * attempt)

        return self._fallback_result(f"LLM调用失败：{last_error}")

    def _call_chat_completions_api(self, payload_text: str) -> dict[str, Any]:
        url = urljoin(OPENAI_BASE_URL.rstrip("/") + "/", "chat/completions")
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        base_body = {
            "model": OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": payload_text},
            ],
            "temperature": OPENAI_TEMPERATURE,
        }

        # 优先使用 json_schema；如果中转接口不支持，再降级到 json_object；再不支持则要求模型纯 JSON 输出。
        bodies = []
        body_schema = dict(base_body)
        body_schema["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "gov_policy_classification",
                "strict": True,
                "schema": JSON_SCHEMA,
            },
        }
        bodies.append(body_schema)

        body_json_object = dict(base_body)
        body_json_object["response_format"] = {"type": "json_object"}
        bodies.append(body_json_object)

        body_plain = dict(base_body)
        body_plain["messages"] = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n请严格按以下JSON Schema字段输出：" + json.dumps(JSON_SCHEMA, ensure_ascii=False)},
            {"role": "user", "content": payload_text},
        ]
        bodies.append(body_plain)

        last_error = ""
        for body in bodies:
            resp = requests.post(url, headers=headers, json=body, timeout=OPENAI_TIMEOUT_SECONDS)
            if resp.status_code >= 400:
                last_error = resp.text[:1000]
                continue
            data = resp.json()
            content = data["choices"][0]["message"].get("content", "")
            return json.loads(_strip_json_code_fence(content))
        raise RuntimeError(f"Chat Completions API调用失败：{last_error}")

    def _call_responses_api(self, payload_text: str) -> dict[str, Any]:
        url = urljoin(OPENAI_BASE_URL.rstrip("/") + "/", "responses")
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        body = {
            "model": OPENAI_MODEL,
            "input": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": payload_text},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "gov_policy_classification",
                    "strict": True,
                    "schema": JSON_SCHEMA,
                }
            },
        }
        resp = requests.post(url, headers=headers, json=body, timeout=OPENAI_TIMEOUT_SECONDS)
        resp.raise_for_status()
        data = resp.json()
        content = _extract_responses_text(data)
        return json.loads(_strip_json_code_fence(content))

    def _build_user_prompt(self, item: dict[str, Any]) -> str:
        text = clean_text(item.get("text", ""))[:LLM_MAX_BODY_CHARS]
        attachments = item.get("attachments") or []
        attachment_lines = []
        for att in attachments[:10]:
            attachment_lines.append(f"- {att.get('name', '附件')} | {att.get('url', '')}")

        rule_info = item.get("rule_info") or {}
        return f"""请判断以下政府网站网页是否应进入周报。

【标题】{item.get('title', '')}
【发布单位】{item.get('source_name', '')}
【地区】{item.get('region', '')}
【部门】{item.get('department', '')}
【发布时间】{item.get('publish_date', '')}
【URL】{item.get('url', '')}
【脚本初判】{json.dumps(rule_info, ensure_ascii=False)}
【附件】
{chr(10).join(attachment_lines) if attachment_lines else '无'}

请特别判断：
1. 这个网页本身是在发布/修订/征求/解读/公示/审批政策文件，还是只是新闻里引用/提到某个文件？
2. 如果只是依据某文件开展活动、工程、会议、宣贯、升级改造，请排除。
3. 如果是安全生产月、培训、警示教育、委员征集等活动/组织类通知，且没有直接影响农药化工企业发展的新义务/许可/申报/补贴，请排除。
4. 如果是单个建设项目环评受理/拟审查/审批决定公示、环评报告书/报告表项目附件，请判为 document_action="项目环评/项目公示" 并排除。

【正文】
{text}
"""

    def _cache_key(self, item: dict[str, Any], payload_text: str) -> str:
        raw = "\n".join(
            [
                "v5-project-eia-exclude",
                str(item.get("url", "")),
                str(item.get("title", "")),
                str(item.get("publish_date", "")),
                payload_text[:8000],
            ]
        )
        return hashlib.sha1(raw.encode("utf-8", errors="ignore")).hexdigest()

    def _normalize_result(self, result: dict[str, Any]) -> dict[str, Any]:
        include = bool(result.get("include"))
        final_category = result.get("final_category") or "exclude"
        document_action = result.get("document_action") or "其他"

        # 二次保险：即使模型误把“仅引用文件/普通新闻活动”设成 include=true，也强制排除。
        if document_action in {"仅引用/提及文件", "普通新闻/活动", "项目环评/项目公示", "其他"}:
            include = False
            result["include"] = False
            result["exclude_reason"] = result.get("exclude_reason") or f"网页主旨为{document_action}，不是发布/修订/征求/解读政策文件"

        if include and not (bool(result.get("is_policy")) or bool(result.get("is_personnel"))):
            include = False
            result["include"] = False
            result["exclude_reason"] = result.get("exclude_reason") or "未被判定为政策文件或人事任免"

        if include and bool(result.get("is_policy")) and result.get("relevance_to_pesticide_chemical_enterprise") in {"none", "low", None, ""}:
            include = False
            result["include"] = False
            result["exclude_reason"] = result.get("exclude_reason") or "与农药化工企业发展相关性不足"

        if not include:
            final_category = "exclude"
            result["final_category"] = "exclude"
            result["is_policy"] = False
            result["is_personnel"] = False
            result["related_directions"] = []
            result["summary"] = ""
            result["change_points"] = []
        else:
            if final_category == "policy":
                result["is_policy"] = True
                result["is_personnel"] = False
            elif final_category == "personnel":
                result["is_policy"] = False
                result["is_personnel"] = True
            elif final_category == "policy_and_personnel":
                result["is_policy"] = True
                result["is_personnel"] = True
        result.setdefault("document_action", document_action)
        result.setdefault("reason", "")
        result.setdefault("exclude_reason", "")
        result.setdefault("summary", "")
        result.setdefault("change_points", [])
        result.setdefault("related_directions", [])
        result.setdefault("confidence", 0.0)
        return result

    def _fallback_result(self, reason: str) -> dict[str, Any]:
        return {
            "include": False,
            "final_category": "exclude",
            "policy_subtype": "none",
            "document_action": "其他",
            "is_personnel": False,
            "is_policy": False,
            "relevance_to_pesticide_chemical_enterprise": "none",
            "related_directions": [],
            "reason": reason,
            "summary": "",
            "change_points": [],
            "exclude_reason": reason,
            "confidence": 0.0,
            "from_cache": False,
        }

    def _load_cache(self) -> None:
        if not self.cache_path or not self.cache_path.exists():
            return
        for line in self.cache_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
                self.cache[obj["key"]] = obj["result"]
            except Exception:
                continue

    def _append_cache(self, key: str, result: dict[str, Any]) -> None:
        if not self.cache_path:
            return
        with self.cache_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"key": key, "result": result}, ensure_ascii=False) + "\n")


def _strip_json_code_fence(text: str) -> str:
    text = (text or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _extract_responses_text(data: dict[str, Any]) -> str:
    if data.get("output_text"):
        return data["output_text"]
    parts: list[str] = []
    for item in data.get("output", []) or []:
        for content in item.get("content", []) or []:
            if content.get("type") in {"output_text", "text"}:
                parts.append(content.get("text", ""))
    return "\n".join(parts).strip()
