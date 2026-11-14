"""Safe, structured diagnostics shared by checkpoints and PDF reports."""

from __future__ import annotations

import re


class NonHtmlContent(RuntimeError):
    """A successful download returned a document instead of an HTML article."""


def failure_details(error):
    # Inspect the exception but never persist raw response text, headers or credentials.
    text = str(error)
    matches = re.findall(r'(?:HTTP\s+|status(?: code)?[=: ]+)([45]\d{2})\b|\b([45]\d{2})\s+(?:Client|Server)\s+Error', text, re.I)
    codes = [a or b for a, b in matches]
    status = int(codes[0]) if codes else None
    reasons = []
    kind = 'request_failed'
    for marker, label, code in (
        ('404', 'HTTP 404：页面不存在或地址已失效', 'not_found'),
        ('403', 'HTTP 403：站点拒绝访问', 'access_blocked'),
        ('412', 'HTTP 412：未通过站点请求校验', 'access_blocked'),
        ('429', 'HTTP 429：请求频率受限', 'rate_limited'),
        ('ERR_BLOCKED_BY_CLIENT', '浏览器阻止请求，具体原因需人工核查', 'browser_blocked'),
        ('访问校验', '浏览器未通过站点访问校验', 'access_blocked'),
    ):
        if (marker in codes) if marker.isdigit() else (marker in text):
            reasons.append(label)
            kind = code
    if 'timeout' in text.lower() or 'timed out' in text.lower() or 'Timeout' in type(error).__name__:
        reasons.append('连接或页面加载超时')
        kind = 'timeout'
    if 'ssl' in text.lower() or 'certificate' in text.lower() or 'SSL' in type(error).__name__:
        reasons.append('SSL 证书校验失败')
        kind = 'tls'
    if not reasons:
        reasons.append(f'HTTP {status}：请求失败' if status else f'请求未成功（{type(error).__name__}）')
    return dict(reason='；'.join(reasons), failure_kind=kind, http_status=status)


def report_issues(context):
    """Use current checkpoint states so a successful retry removes stale warnings."""
    result, seen = [], set()
    for source in (context.get('coverage') or {}).get('sources', []):
        for kind, entries in (('list', source.get('details', [])), ('detail', source.get('issues', []))):
            for entry in entries:
                if entry.get('status') not in {'failed', 'empty', 'pending', 'detail_failed'}:
                    continue
                item = dict(entry, source=source.get('name', ''), kind=kind)
                key = (item['source'], item.get('url', ''), kind)
                if key not in seen:
                    seen.add(key)
                    result.append(item)
    return result
