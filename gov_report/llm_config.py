"""LLM configuration from environment variables or local desktop settings."""

import json
import os
import sys
from pathlib import Path


def _load_local_settings() -> dict:
    app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    try:
        settings = json.loads((app_dir / "user_settings.json").read_text(encoding="utf-8"))
        return settings if isinstance(settings, dict) else {}
    except (OSError, ValueError):
        return {}


_settings = _load_local_settings()
OPENAI_API_KEY = os.getenv("GOV_REPORT_OPENAI_API_KEY") or _settings.get("openai_api_key", "")
OPENAI_BASE_URL = os.getenv("GOV_REPORT_OPENAI_BASE_URL") or _settings.get("openai_base_url") or "https://api.openai.com/v1"
OPENAI_MODEL = os.getenv("GOV_REPORT_OPENAI_MODEL") or _settings.get("openai_model") or "gpt-5.4"
OPENAI_API_STYLE = os.getenv("GOV_REPORT_OPENAI_API_STYLE") or "auto"

OPENAI_TIMEOUT_SECONDS = 90
OPENAI_MAX_RETRIES = 3
OPENAI_TEMPERATURE = 0
LLM_MAX_BODY_CHARS = 6000
ENABLE_LLM_CACHE = True
