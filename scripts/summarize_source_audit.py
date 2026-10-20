"""Summarize saved live checks and optionally refresh verified collection seeds."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scripts.audit_sources import inspect_html
from gov_report.parser import ATTACHMENT_EXTS
CORE = re.compile(r"政策|法规|规章|规范性|文件|通知|公告|公示|人事|任免|许可|审批|标准|农药")
EXCLUDE = re.compile(r"网站声明|信息公开指南|信息公开制度|信息公开年报|年度报告|依申请|公开申请|信箱|举报|投诉|领导活动|新闻发布会|归档")
ERROR_TITLES = {"403", "404", "412", "500", "502", "page not found", "access denied"}


def load_reports(directories: list[Path]) -> dict:
    merged = {}
    for directory in directories:
        for path in sorted(directory.glob("*/audit.json")):
            result = json.loads(path.read_text(encoding="utf-8"))
            index = int(path.parent.name)
            target = merged.setdefault(index, {"source": result["source"], "pages": {}, "passes": [], "superseded_probes": [], "nonhtml_probes": set()})
            target["passes"].append({"directory": str(path.parent), "complete": "unvisited_urls" in result,
                                     "depth": result.get("depth"), "unvisited": result.get("unvisited_urls", [])})
            target["passes"][-1]["complete"] = target["passes"][-1]["complete"] and not result.get("unvisited_urls")
            for page in result["pages"]:
                if Path(urlparse(page["url"]).path).suffix.lower() in ATTACHMENT_EXTS:
                    target["nonhtml_probes"].add(page["url"])
                    continue
                page = dict(page)
                page["evidence_directory"] = str(path.parent)
                if page.get("ok") and page.get("title", "").strip().lower() in ERROR_TITLES:
                    page.update(ok=False, content_error="HTTP success returned an error-page document")
                target["pages"][page["url"]] = page
    for site in merged.values():
        for url in list(site["pages"]):
            if "/common/getChannelListchannelCode=" not in url:
                continue
            corrected = url.replace("/common/getChannelListchannelCode=", "/common/getChannelList?channelCode=", 1)
            replacement = site["pages"].get(corrected)
            if replacement:
                site["superseded_probes"].append({"old_url": url, "corrected_url": corrected, "ok": bool(replacement.get("ok"))})
                del site["pages"][url]
    return merged


def verified_channels(site: dict) -> dict[str, str]:
    pages = site["pages"]
    aliases = dict(pages)
    for page in pages.values():
        if page.get("ok") and page.get("final_url"):
            aliases.setdefault(page["final_url"], page)
    root = pages.get(site["source"]["base_url"], {})
    root_url = urlparse(root.get("final_url", site["source"]["base_url"]))
    channels = {}
    for page in pages.values():
        if not page.get("ok") or page.get("reason") == "article_sample":
            continue
        for link in page.get("links", []):
            label = re.sub(r"\s+", "", link["label"])
            if not link.get("channel") or not CORE.search(label) or EXCLUDE.search(label):
                continue
            checked = aliases.get(link["url"])
            if checked and checked.get("ok") and checked.get("reason") != "article_sample":
                url = checked.get("final_url", link["url"])
                parsed = urlparse(url)
                if parsed.hostname == root_url.hostname and parsed.path.rstrip("/") == root_url.path.rstrip("/"):
                    continue
                if parsed.fragment or re.search(r"login|signin|/sso/|/bssx/", parsed.path, re.I):
                    continue
                if re.match(r"(?:ucenter|ythzxfw|std|jwxk|zwfw)\.", parsed.hostname or "", re.I):
                    continue
                if re.search(r"登录|统一身份认证", checked.get("title", "")):
                    continue
                has_content = any(x.get("article") and x.get("same_site") for x in checked.get("links", []))
                has_columns = any(x.get("channel") and CORE.search(x["label"]) and x["url"] != link["url"] for x in checked.get("links", []))
                if not has_content and not has_columns:
                    continue
                if not re.search(r"/common/search/", url) or "page=1" in url:
                    channels.setdefault(url, label)
    return channels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directories", type=Path, nargs="+")
    parser.add_argument("--date", default="2026-10-18")
    parser.add_argument("--report", type=Path, default=ROOT / "docs/site-audit-2026-10-18.md")
    parser.add_argument("--inventory", type=Path, default=ROOT / "audit-results/site-control-inventory.csv")
    parser.add_argument("--navigation", type=Path, default=ROOT / "audit-results/site-navigation-inventory.csv")
    parser.add_argument("--reinspect-snapshots", action="store_true", help="Re-read saved HTML with the current navigation/control parser")
    parser.add_argument("--write-config", action="store_true")
    args = parser.parse_args()
    sites = load_reports(args.directories)
    if len(sites) != 30 or any(not all(x["complete"] for x in s["passes"]) for s in sites.values()):
        raise RuntimeError("All 30 source checks and selected supplemental passes must finish before summarizing")
    if args.reinspect_snapshots:
        for index, site in sorted(sites.items()):
            for page in site["pages"].values():
                if page.get("ok") and page.get("snapshot"):
                    snapshot = Path(page["evidence_directory"]) / page["snapshot"]
                    page.update(inspect_html(snapshot.read_text(encoding="utf-8"), page["final_url"], site["source"]["base_url"]))
            print(f"Reinspected source {index:02d}", flush=True)

    lines = [f"# 30 个政府网站栏目与控件检查记录（{args.date}）", "",
             "检查对象为软件 config/sources.yaml 中的 30 个站点。逐站请求当前公开页面，保存栏目、按钮、检索表单、下拉选项、iframe 和脚本信息，并抽查列表翻页及详情页。", "",
             "范围说明：主检查从首页与配置入口递归两层，部分动态目录另做补查；不等同于对政府网站所有历史页面或全部业务功能进行人工验收。按钮/表单项记录其入口和参数，未填写或提交登录、申请、举报、缴费等表单，也未使用个人 API Key。", "",
             "控件数量是逐页累计记录，同一导航会在多个页面重复出现；HTTP 可达、页面可解析与按钮业务功能正常是不同检查项。", "",
             "页面记录按站点和请求 URL 去重，包含栏目、公开接口及详情抽样；HTTP/HTTPS 别名可能分开计数。非 HTML 附件不作为网页失败统计，修复前拼接错误的目录地址由重查结果替代，原始记录仍保留。", "",
             "## 逐站结果", "",
             "| # | 网站 | 页面检查 | 页面可达 | 失败/待复核 | 控件记录 | 已验证采集入口 |", "| --- | --- | ---: | ---: | ---: | ---: | ---: |"]
    summary = []
    for index, site in sorted(sites.items()):
        pages = list(site["pages"].values())
        channels = verified_channels(site)
        ok = sum(bool(x.get("ok")) for x in pages)
        controls = sum(len(x.get("controls", [])) for x in pages)
        lines.append(f"| {index} | {site['source']['name']} | {len(pages)} | {ok} | {len(pages)-ok} | {controls} | {len(channels)} |")
        summary.append({"index": index, "name": site["source"]["name"], "checked_pages": len(pages),
                        "accessible_pages": ok, "failed_pages": len(pages)-ok, "control_records": controls,
                        "superseded_probes": site["superseded_probes"], "nonhtml_probe_count": len(site["nonhtml_probes"]),
                        "verified_channels": channels})
    lines += ["", "## 本地修复", "",
              "- 解析江苏 JCMS 列表中脚本/XML 的记录与翻页入口。", "- 读取公共脚本中写入的导航，跟随同站点桌面跳转。",
              "- 递归发现子栏目，处理普通下一页、TRS 分页及 JCMS 分组分页。", "- 识别黑龙江动态分类和公开列表查询接口，保留发布日期并继续分页。",
              "- 读取南通脚本生成的折叠菜单和 TrueCMS 分组记录，保留检索与下拉选项。",
              "- 适配工信部政策文件库公开查询及动态栏目接口；湖北 h5 列表不再被误当文章。",
              "- 对工信部等动态列表及访问校验页面使用浏览器渲染；浏览器仍报错时明确记录失败。", "- 栏目、分页链接不再作为详情页重复抓取，文章日期优先使用发布元数据。",
              "- 0 表示不限制栏目/详情数量；已有 UI 的无上限模式同步使用该值。", "",
              "## 入口与异常明细", ""]
    for index, site in sorted(sites.items()):
        lines += [f"### {index:02d} {site['source']['name']}", ""]
        root = site["pages"].get(site["source"]["base_url"], {})
        lines += [f"- 首页：{root.get('final_url', site['source']['base_url'])}"]
        browser_pages = sum(any(x.get("method", "").startswith("browser") for x in p.get("attempts", [])) for p in site["pages"].values())
        lines += [f"- 浏览器渲染/兜底页面：{browser_pages}。"]
        for url, label in verified_channels(site).items():
            lines.append(f"- 已核验入口：[{label}]({url})")
        failures = [p for p in site["pages"].values() if not p.get("ok")]
        if not failures:
            lines.append("- 本次请求未记录页面访问失败；表单提交与需登录业务功能未作通过判定。")
        for page in failures:
            attempt = next((x for x in reversed(page.get("attempts", [])) if x.get("error") or x.get("status")), {})
            reason = page.get("content_error") or attempt.get("error") or f"HTTP {attempt.get('status', 'unknown')}"
            lines.append(f"- 待复核：[页面]({page['url']})；{str(reason).replace(chr(10), ' ')[:350]}")
        lines.append("")
    lines += ["## 证据", "", "原始逐页结果保存在本地 audit-results/ 下各轮检查目录的站点编号/audit.json，HTML 快照与其同目录。",
              "完整控件记录见 audit-results/site-control-inventory.csv，包含站点、页面、控件类型、标签、请求入口、表单方法、下拉选项及公开控件参数。",
              "栏目与导航链接见 audit-results/site-navigation-inventory.csv，按站点、目标 URL 和标签去重；未请求的外站入口不标记为通过。", ""]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines), encoding="utf-8")
    args.report.with_suffix(".json").write_text(json.dumps({"checked_at": datetime.now().astimezone().isoformat(), "sites": summary}, ensure_ascii=False, indent=2), encoding="utf-8")

    args.inventory.parent.mkdir(parents=True, exist_ok=True)
    with args.inventory.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["站点", "页面", "页面标题", "控件类型", "输入类型", "名称", "标签", "请求入口", "方法", "下拉选项", "公开参数", "事件", "检查方式"])
        for site in sites.values():
            for page in site["pages"].values():
                for control in page.get("controls", []):
                    writer.writerow([site["source"]["name"], page["url"], page.get("title", ""), control["tag"],
                                     control.get("type", ""), control.get("name", ""), control.get("label", ""),
                                     control.get("action", ""), control.get("method", ""),
                                     json.dumps(control.get("options", []), ensure_ascii=False),
                                     json.dumps({**control.get("data_attributes", {}), **control.get("parameters", {})}, ensure_ascii=False),
                                     control.get("onclick", ""), "仅识别与读取，未提交表单"])
    args.navigation.parent.mkdir(parents=True, exist_ok=True)
    with args.navigation.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["站点", "发现页面", "栏目/链接名称", "链接", "同站", "栏目", "文章", "页面请求结果"])
        for site in sites.values():
            seen = set()
            for page in site["pages"].values():
                for link in page.get("links", []):
                    key = (link["url"], link["label"])
                    if key in seen:
                        continue
                    seen.add(key)
                    checked = site["pages"].get(link["url"])
                    status = "请求成功" if checked and checked.get("ok") else "失败/待复核" if checked else "未请求（超出本轮范围或外站）"
                    if link.get("attachment"):
                        status = "附件链接（仅记录，未下载）"
                    elif link.get("request_excluded"):
                        status = "操作入口（仅记录，未执行）"
                    writer.writerow([site["source"]["name"], page["url"], link["label"], link["url"],
                                     link.get("same_site"), link.get("channel"), link.get("article"), status])
    if args.write_config:
        path = ROOT / "config/sources.yaml"
        sources = yaml.safe_load(path.read_text(encoding="utf-8"))
        for index, source in enumerate(sources, 1):
            site = sites[index]
            if source["name"] != site["source"]["name"]:
                raise RuntimeError("Source ordering changed during the audit")
            root = site["pages"].get(source["base_url"], {})
            if root.get("ok"):
                source["base_url"] = root["final_url"]
            channels = verified_channels(site)
            if not channels:
                raise RuntimeError(f"No verified collection seed for {source['name']}; existing configuration was not replaced")
            source["list_urls"] = list(channels)
            source["channel_names"] = channels
            source["last_checked"] = args.date
        header = "# 根据逐站公开页面检查更新，具体范围和异常见 docs/site-audit-2026-10-18.md。\n"
        temporary = path.with_suffix(".yaml.tmp")
        temporary.write_text(header + yaml.safe_dump(sources, allow_unicode=True, sort_keys=False, width=140), encoding="utf-8")
        temporary.replace(path)
    print(json.dumps({"sites": len(summary), "pages": sum(s["checked_pages"] for s in summary),
                      "failed_pages": sum(s["failed_pages"] for s in summary),
                      "controls": sum(s["control_records"] for s in summary),
                      "channels": sum(len(s["verified_channels"]) for s in summary),
                      "report": str(args.report)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
