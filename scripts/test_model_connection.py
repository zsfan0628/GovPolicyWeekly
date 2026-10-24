"""Make one short classification using the desktop's saved model configuration.

This calls the configured service and may incur a small API charge. No site crawl,
raw response, API key, or private endpoint address is printed or saved.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main() -> int:
    from gov_report.desktop import SettingsStore
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settings", type=Path, help="Optional local desktop settings file")
    args = parser.parse_args()
    store = SettingsStore(args.settings) if args.settings else SettingsStore()
    settings = store.load()
    for name, key in (("BASE_URL", "openai_base_url"), ("API_KEY", "openai_api_key"), ("MODEL", "openai_model")):
        value = settings.get(key)
        if not isinstance(value, str) or not value.strip():
            print("模型配置不完整，请先在桌面界面保存地址、密钥和模型")
            return 1
        os.environ["GOV_REPORT_OPENAI_" + name] = value.strip()
    from gov_report.llm_classifier import LLMClassifier
    classifier = LLMClassifier(cache_enabled=False)
    started = time.perf_counter()
    result = classifier.classify_article({
        "title": "化工企业技术改造项目申报通知（接口测试样例）", "source_name": "本地接口测试",
        "text": "这是用于验证软件接口的虚构测试样例，不是真实政府文件。现组织化工企业申报技术改造专项资金，"
                "符合条件的工业企业可按新增条件提交材料申请补贴。请按既定结构返回判断。",
    })
    output = {"ok": result.get("call_succeeded") is True, "model": settings["openai_model"],
              "api_style": result.get("api_style", ""), "response_mode": result.get("response_mode", ""),
              "api_prefix": result.get("api_prefix", ""), "seconds": round(time.perf_counter() - started, 2)}
    if not output["ok"]:
        output["error"] = result.get("reason", "未取得有效模型判断")
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0 if output["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
