from __future__ import annotations

import re
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from dateutil import parser as dt_parser

try:
    TZ = ZoneInfo("Asia/Shanghai")
except Exception:
    TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")


def resolve_date_range(
    days: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
    include_today: bool = False,
) -> tuple[datetime, datetime]:
    """解析统计区间。

    默认：当前日期之前 7 天，不包含今天。
    例如 2026-05-30 运行，days=7，则为 2026-05-23 00:00:00 到 2026-05-29 23:59:59。
    """
    if start_date or end_date:
        if not start_date or not end_date:
            raise ValueError("--start-date 和 --end-date 必须同时提供")
        start = datetime.combine(date.fromisoformat(start_date), time.min, tzinfo=TZ)
        end = datetime.combine(date.fromisoformat(end_date), time.max, tzinfo=TZ)
        if end < start:
            raise ValueError("end-date 不能早于 start-date")
        return start, end

    if days <= 0:
        raise ValueError("--days 必须大于 0")

    today = datetime.now(TZ).date()
    if include_today:
        end_day = today
        start_day = today - timedelta(days=days - 1)
    else:
        end_day = today - timedelta(days=1)
        start_day = today - timedelta(days=days)

    start = datetime.combine(start_day, time.min, tzinfo=TZ)
    end = datetime.combine(end_day, time.max, tzinfo=TZ)
    return start, end


def in_range(dt: datetime | None, start: datetime, end: datetime) -> bool:
    if dt is None:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ)
    return start <= dt <= end


_DATE_PATTERNS = [
    re.compile(r"(?P<y>20\d{2})[-/.年](?P<m>\d{1,2})[-/.月](?P<d>\d{1,2})日?"),
    re.compile(r"(?P<y>20\d{2})(?P<m>\d{2})(?P<d>\d{2})"),
]


def parse_cn_date(text: str | None) -> datetime | None:
    """从中文政府网站标题、父节点文本、URL 中提取日期。"""
    if not text:
        return None
    text = str(text)
    for pat in _DATE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        try:
            y = int(m.group("y"))
            mon = int(m.group("m"))
            d = int(m.group("d"))
            return datetime(y, mon, d, tzinfo=TZ)
        except ValueError:
            pass

    # 兜底：dateutil 对部分英文/数字日期有用，但避免把纯数字编号误识别为日期。
    if re.search(r"20\d{2}", text):
        try:
            parsed = dt_parser.parse(text, fuzzy=True, default=datetime(2000, 1, 1))
            if 2000 <= parsed.year <= 2100:
                return parsed.replace(tzinfo=TZ)
        except Exception:
            return None
    return None


def fmt_date(dt: datetime | None) -> str:
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d")
