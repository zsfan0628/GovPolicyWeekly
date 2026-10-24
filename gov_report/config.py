from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .scope import apply_scope


def load_yaml(path: str | Path) -> Any:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_sources(path: str | Path) -> list[dict[str, Any]]:
    data = load_yaml(path)
    if not isinstance(data, list):
        raise ValueError(f"sources.yaml 应为列表格式: {path}")
    for source in data:
        if "name" not in source or "base_url" not in source:
            raise ValueError(f"站点配置缺少 name/base_url: {source}")
        source.setdefault("list_urls", [])
        source.setdefault("region", "")
        source.setdefault("department", "")
    scope_path = Path(path).parent / "crawl_scope.yaml"
    if not scope_path.exists():
        scope_path = Path(__file__).resolve().parent.parent / "config" / "crawl_scope.yaml"
    policy = load_yaml(scope_path) if scope_path.exists() else {}
    return [apply_scope(source, policy) if "crawl_scope" not in source else source for source in data]


def load_keywords(path: str | Path) -> dict[str, list[str]]:
    data = load_yaml(path)
    if not isinstance(data, dict):
        raise ValueError(f"keywords.yaml 应为字典格式: {path}")
    for key in ["personnel", "policy", "change"]:
        data.setdefault(key, [])
    return data
