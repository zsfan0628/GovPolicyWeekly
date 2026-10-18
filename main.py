from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from gov_report.config import load_keywords, load_sources
from gov_report.crawler import GovCrawler, read_manual_urls, dedupe_records
from gov_report.date_utils import resolve_date_range
from gov_report.report import export_all


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="政府网站人事任免与农药化工政策信息手动周报采集脚本")
    p.add_argument("--days", type=int, default=7, help="统计当前日期之前多少天，默认7天；默认不包含今天")
    p.add_argument("--include-today", action="store_true", help="统计区间包含今天。默认不包含今天")
    p.add_argument("--start-date", type=str, default=None, help="指定开始日期，例如 2026-05-23")
    p.add_argument("--end-date", type=str, default=None, help="指定结束日期，例如 2026-05-29")
    p.add_argument("--source", type=str, default=None, help="只调试某一个站点，名称需与 config/sources.yaml 一致")
    p.add_argument("--sources", type=str, default="config/sources.yaml", help="站点配置文件")
    p.add_argument("--keywords", type=str, default="config/keywords.yaml", help="关键词配置文件")
    p.add_argument("--manual-urls", type=str, default="input/manual_urls.txt", help="手工补充URL文件，一行一个")
    p.add_argument("--output-root", type=str, default="output", help="输出根目录")
    p.add_argument("--max-channels-per-source", type=int, default=10, help="每个站点首页自动发现的栏目页数量上限")
    p.add_argument("--max-detail-per-source", type=int, default=80, help="每个站点最多进入详情页数量，防止过慢")
    p.add_argument("--no-download-attachments", action="store_true", help="只记录附件链接，不下载附件")
    p.add_argument("--sleep", type=float, default=0.5, help="每次请求之间的间隔秒数")
    p.add_argument("--no-verify-ssl", action="store_true", help="关闭SSL证书校验，少数旧政府网站证书异常时可用")
    p.add_argument("--loose", action="store_true", help="宽松模式：接近旧版，会议/动态类也可能被收录；默认是严格模式")
    p.add_argument("--no-llm", action="store_true", help="关闭 GPT-5.5 复判；默认在 llm_config.py 填写 API_KEY 后启用")
    p.add_argument("--browser-fallback", action="store_true", default=True, help="遇到403/412/重定向异常时，尝试用 Playwright 浏览器方式读取。v5.2默认启用。需另行安装 playwright。")
    p.add_argument("--no-browser-fallback", action="store_true", help="关闭 Playwright 浏览器兜底读取。")
    p.add_argument("--allow-rule-fallback", action="store_true", help="当GPT未启用时，允许模糊候选按规则兜底通过。默认关闭，避免半信半疑内容进入报告。")
    return p.parse_args()


def main() -> None:
    run_start_ts = time.perf_counter()
    args = parse_args()
    start, end = resolve_date_range(
        days=args.days,
        start_date=args.start_date,
        end_date=args.end_date,
        include_today=args.include_today,
    )
    out_dir = Path(args.output_root) / f"{start:%Y-%m-%d}_至_{end:%Y-%m-%d}"
    out_dir.mkdir(parents=True, exist_ok=True)

    sources = load_sources(args.sources)
    keywords = load_keywords(args.keywords)

    print(f"统计周期：{start:%Y-%m-%d %H:%M:%S} 至 {end:%Y-%m-%d %H:%M:%S}")
    print(f"输出目录：{out_dir}")

    crawler = GovCrawler(
        sources=sources,
        keywords=keywords,
        output_dir=out_dir,
        max_channels_per_source=args.max_channels_per_source,
        max_detail_per_source=args.max_detail_per_source,
        download_attachments=not args.no_download_attachments,
        sleep=args.sleep,
        verify_ssl=not args.no_verify_ssl,
        strict=not args.loose,
        use_llm=not args.no_llm,
        browser_fallback=(args.browser_fallback and not args.no_browser_fallback),
        allow_rule_fallback=args.allow_rule_fallback,
    )

    records = crawler.crawl(start, end, source_name=args.source)
    manual_urls = read_manual_urls(args.manual_urls)
    if manual_urls:
        print(f"读取手工补充链接 {len(manual_urls)} 条")
        records.extend(crawler.crawl_manual_urls(manual_urls, start, end))

    # 再去重一次：同时按规范化URL、标题+日期+来源、正文hash去重。
    records = dedupe_records(records)
    records = sorted(records, key=lambda x: (x.get("publish_date", ""), x.get("source_name", "")), reverse=True)

    paths = export_all(records, out_dir, start, end, keywords)

    elapsed = time.perf_counter() - run_start_ts
    elapsed_text = format_duration(elapsed)
    runtime_info = {
        "elapsed_seconds": round(elapsed, 3),
        "elapsed_text": elapsed_text,
        "record_count": len(records),
        "start_date": f"{start:%Y-%m-%d %H:%M:%S}",
        "end_date": f"{end:%Y-%m-%d %H:%M:%S}",
    }
    (out_dir / "runtime_summary.json").write_text(json.dumps(runtime_info, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "crawl_log.txt").open("a", encoding="utf-8") as f:
        f.write(f"\n程序运行总时长：{elapsed_text}（{elapsed:.3f} 秒）\n")

    print("\n生成完成：")
    for k, v in paths.items():
        if v:
            print(f"- {k}: {v}")
        elif k == "pdf":
            print("- pdf: 未生成。请安装 LibreOffice 后重试，或直接打开 DOCX。")
    print(f"- log: {out_dir / 'crawl_log.txt'}")
    print(f"- runtime: {out_dir / 'runtime_summary.json'}")
    print(f"共命中 {len(records)} 条。")
    print(f"程序运行总时长：{elapsed_text}")
    print("GPT复判配置在 gov_report/llm_config.py 中修改；如需关闭，用 --no-llm。")
    print("v5.2 默认启用浏览器兜底；若提示未安装 Playwright，请执行：pip install playwright && python -m playwright install chromium")


def format_duration(seconds: float) -> str:
    seconds_int = int(round(seconds))
    h, rem = divmod(seconds_int, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}小时{m}分{sec}秒"
    if m:
        return f"{m}分{sec}秒"
    return f"{sec}秒"


if __name__ == "__main__":
    main()
