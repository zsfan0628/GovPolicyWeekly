"""One synthetic classification through the production transport, without caches."""

import time


def run_probe():
    from .llm_classifier import LLMClassifier
    started = time.perf_counter()
    result = LLMClassifier(cache_enabled=False).classify_article({
        "title": "化工企业技术改造项目申报通知（虚构接口测试样例）",
        "source_name": "本地接口测试",
        "text": "这是虚构测试样例，不是真实政府文件。现组织化工企业申报技术改造专项资金，"
                "符合条件的工业企业可按新增条件提交材料申请补贴。请按既定结构返回判断。",
    })
    return dict(ok=result.get("call_succeeded") is True, seconds=round(time.perf_counter() - started, 2),
                model=result.get("model", ""), api_style=result.get("api_style", ""),
                response_mode=result.get("response_mode", ""),
                error="" if result.get("call_succeeded") else result.get("reason", "未取得有效判断"))
