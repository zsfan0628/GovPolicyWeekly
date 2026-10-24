"""Decode compatible API responses without exposing credentials or raw page contents."""

from __future__ import annotations

import json
import math
import re
from urllib.parse import urlsplit, urlunsplit

import requests


class ModelCallError(RuntimeError):
    def __init__(self, message: str, *, kind: str = "format", retryable: bool = False):
        super().__init__(message)
        self.kind = kind
        self.retryable = retryable


def api_bases(value: str) -> list[str]:
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password or parts.query or parts.fragment:
        raise ModelCallError("API 根地址格式不正确", kind="configuration")
    path = parts.path.rstrip("/")
    for suffix in ("/chat/completions", "/responses", "/models"):
        if path.endswith(suffix):
            path = path[:-len(suffix)]
            break
    base = urlunsplit((parts.scheme, parts.netloc, path, "", ""))
    # Never guess a different provider, host or arbitrary custom prefix.
    return [base, base + "/v1"] if not path else [base]


def _message_text(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "".join(_message_text(part.get("text", "")) for part in value
                       if isinstance(part, dict) and part.get("type") in {"text", "output_text"})
    if isinstance(value, dict) and isinstance(value.get("value"), str):
        return value["value"]
    return ""


def _response_text(data: dict):
    if data.get("status") in {"failed", "incomplete", "cancelled"}:
        raise ModelCallError("Responses 返回未完成或失败状态，未取得完整判断", kind="incomplete")
    if isinstance(data.get("output_text"), str) and data["output_text"].strip():
        return data["output_text"]
    parts = []
    for item in data.get("output", []) or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content") or []
        if any(isinstance(part, dict) and part.get("type") == "refusal" for part in content):
            raise ModelCallError("模型拒绝回答，未完成文章判断", kind="refusal")
        parts.append(_message_text(content))
    return "\n".join(parts).strip()


def _model_content(data: dict):
    if isinstance(data.get("choices"), list) and data["choices"]:
        choice = data["choices"][0]
        if not isinstance(choice, dict):
            raise ModelCallError("生成接口的 choices 结构不正确")
        if choice.get("finish_reason") in {"length", "content_filter"}:
            raise ModelCallError("模型回答被截断或过滤，未取得完整判断", kind="incomplete")
        message = choice.get("message") or {}
        if not isinstance(message, dict):
            raise ModelCallError("生成接口的 message 结构不正确")
        if message.get("refusal"):
            raise ModelCallError("模型拒绝回答，未完成文章判断", kind="refusal")
        parsed = message.get("parsed")
        return parsed if isinstance(parsed, dict) else _message_text(message.get("content"))
    if "output" in data or "output_text" in data:
        return _response_text(data)
    raise ModelCallError("生成接口未返回 choices/message 或 Responses output，可能并非生成接口")


def parse_judgment(content, schema: dict) -> dict:
    if isinstance(content, dict):
        values = [content]
    else:
        text = _message_text(content).strip().lstrip("\ufeff")
        if not text:
            raise ModelCallError("模型回答为空，未取得 JSON 判断")
        # Never interpret a reasoning block as the final classification.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.S | re.I).strip()
        decoder = json.JSONDecoder()
        values = []
        for match in re.finditer(r"\{", text):
            try:
                value, _ = decoder.raw_decode(text, match.start())
                if isinstance(value, dict):
                    values.append(value)
            except ValueError:
                continue
        if not values:
            raise ModelCallError("模型回答不是完整 JSON 对象，请检查模型的结构化输出支持")
    for value in values:
        if not all(key in value for key in schema["required"]):
            continue
        valid = True
        for key, spec in schema["properties"].items():
            item = value[key]
            kind = spec["type"]
            valid = valid and ((kind == "boolean" and type(item) is bool)
                               or (kind == "string" and isinstance(item, str))
                               or (kind == "array" and isinstance(item, list) and all(isinstance(x, str) for x in item))
                               or (kind == "number" and type(item) in {int, float} and math.isfinite(item)
                                   and spec.get("minimum", -math.inf) <= item <= spec.get("maximum", math.inf)))
            if "enum" in spec:
                valid = valid and item in spec["enum"]
            if kind == "array" and isinstance(item, list) and "enum" in spec["items"]:
                valid = valid and all(x in spec["items"]["enum"] for x in item)
        if valid:
            return {key: value[key] for key in schema["properties"]}
    raise ModelCallError("模型 JSON 缺少判断字段或字段类型不正确，未把它当作排除结果")


def _event_stream(raw: str, schema: dict) -> dict:
    fragments = []
    completed = None
    finished = False
    for block in re.split(r"\r?\n\r?\n", raw):
        payload = "\n".join(line[5:].lstrip() for line in block.splitlines() if line.startswith("data:"))
        if not payload:
            continue
        if payload == "[DONE]":
            finished = True
            continue
        try:
            data = json.loads(payload)
        except ValueError:
            raise ModelCallError("事件流含有无法解析的 JSON 片段") from None
        if not isinstance(data, dict):
            raise ModelCallError("事件流片段不是对象")
        event_type = data.get("type", "")
        if data.get("error") or event_type in {"error", "response.failed", "response.incomplete"}:
            raise ModelCallError("生成接口事件流返回失败或未完成状态", kind="incomplete")
        if event_type in {"response.refusal.delta", "response.refusal.done"}:
            raise ModelCallError("模型拒绝回答，未完成文章判断", kind="refusal")
        if event_type == "response.completed":
            completed = data.get("response")
            finished = True
        elif event_type == "response.output_text.delta":
            fragments.append(_message_text(data.get("delta")))
        for choice in data.get("choices", []) or []:
            if choice.get("index", 0) != 0:
                continue
            if choice.get("finish_reason") in {"length", "content_filter"}:
                raise ModelCallError("模型事件流被截断或过滤", kind="incomplete")
            delta = choice.get("delta") or {}
            if delta.get("refusal"):
                raise ModelCallError("模型拒绝回答，未完成文章判断", kind="refusal")
            fragments.append(_message_text(delta.get("content")))
            finished = finished or choice.get("finish_reason") == "stop"
    if not finished:
        raise ModelCallError("生成接口事件流中断，未取得完成标记", kind="incomplete", retryable=True)
    return parse_judgment(_response_text(completed) if isinstance(completed, dict) else "".join(fragments), schema)


def decode_response(response, schema: dict) -> dict:
    status = response.status_code
    mime = response.headers.get("Content-Type", "").split(";", 1)[0].lower()
    raw = response.text.lstrip("\ufeff \r\n\t")
    meta = f"HTTP {status}，响应类型 {mime or '未声明'}"
    if status in {401, 402, 403}:
        raise ModelCallError(f"{meta}；请检查密钥、余额或所选模型的生成权限", kind="authorization")
    if status == 429 or status >= 500:
        raise ModelCallError(f"{meta}；接口限流或服务暂时异常", kind="transient", retryable=True)
    if status in {404, 405} or 300 <= status < 400:
        raise ModelCallError(f"{meta}；未找到生成接口或返回了跳转", kind="endpoint")
    if status >= 400:
        kind = "format"
        # Inspect messages for parameter negotiation, but never copy server text into logs.
        try:
            payload = response.json()
            error = payload.get("error") if isinstance(payload, dict) else None
            detail = json.dumps(error, ensure_ascii=False).lower()
            if "temperature" in detail:
                kind = "temperature"
        except ValueError:
            pass
        raise ModelCallError(f"{meta}；生成参数不被支持或请求被拒绝", kind=kind)
    if mime == "text/html" or raw.lower().startswith(("<!doctype html", "<html")):
        raise ModelCallError(f"{meta}；返回的是网站 HTML 页面，不是模型 API，请检查 API 根路径", kind="endpoint")
    if not raw:
        raise ModelCallError(f"{meta}；接口响应为空")
    try:
        if mime == "text/event-stream" or raw.startswith(("data:", "event:")):
            return _event_stream(raw, schema)
        try:
            data = response.json()
        except ValueError:
            raise ModelCallError("接口响应不是 JSON（未记录原始内容以保护隐私）") from None
        if not isinstance(data, dict):
            raise ModelCallError("生成接口返回的 JSON 顶层不是对象")
        if data.get("error"):
            raise ModelCallError("接口返回 error 对象，未取得模型判断")
        return parse_judgment(_model_content(data), schema)
    except ModelCallError as error:
        raise ModelCallError(f"{meta}；{error}", kind=error.kind, retryable=error.retryable) from None


def post_judgment(url: str, headers: dict, body: dict, timeout: int, schema: dict) -> dict:
    try:
        response = requests.post(url, headers=headers, json=body, timeout=(10, timeout), allow_redirects=False)
    except requests.RequestException as error:
        raise ModelCallError(f"网络请求失败（{type(error).__name__}），未取得模型判断",
                             kind="network", retryable=True) from None
    try:
        return decode_response(response, schema)
    finally:
        response.close()
