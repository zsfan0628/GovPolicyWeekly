from __future__ import annotations

import argparse
import json
import time
import uuid
from pathlib import Path

from gov_report.config import load_keywords, load_sources
from gov_report.crawler import GovCrawler, read_manual_urls, dedupe_records
from gov_report.date_utils import resolve_date_range
from gov_report.report import export_all
from gov_report.task_state import TaskState, task_lock


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
    p.add_argument("--max-channels-per-source", type=int, default=0, help="每个站点自动发现的栏目数量上限；0为不限")
    p.add_argument("--max-detail-per-source", type=int, default=0, help="每个站点详情抓取数量上限；0为不限")
    attachments = p.add_mutually_exclusive_group()
    attachments.add_argument("--download-attachments", action="store_true", help="PDF 生成后下载附件；默认只保留附件链接")
    attachments.add_argument("--no-download-attachments", action="store_true", help="只记录附件链接，不下载附件（默认）")
    p.add_argument("--workers", type=int, choices=range(1, 7), default=3, help="同时采集的站点数，默认3；同一站点仍顺序访问")
    p.add_argument("--full-scan", action="store_true", help="维护模式：完整入口清单，不按日期停止翻页")
    p.add_argument("--no-cache", action="store_true", help="关闭正文和模型判断缓存，用于核对采集结果")
    p.add_argument("--cache-dir", type=str, default=None, help="跨日期范围共享的缓存目录，默认输出根目录下的 .cache")
    p.add_argument("--sleep", type=float, default=0.5, help="每次请求之间的间隔秒数")
    p.add_argument("--no-verify-ssl", action="store_true", help="关闭SSL证书校验，少数旧政府网站证书异常时可用")
    p.add_argument("--loose", action="store_true", help="宽松模式：接近旧版，会议/动态类也可能被收录；默认是严格模式")
    p.add_argument("--no-llm", action="store_true", help="关闭 GPT-5.5 复判；默认在 llm_config.py 填写 API_KEY 后启用")
    p.add_argument("--browser-fallback", action="store_true", default=True, help="遇到403/412/重定向异常时，尝试用 Playwright 浏览器方式读取。v5.2默认启用。需另行安装 playwright。")
    p.add_argument("--no-browser-fallback", action="store_true", help="关闭 Playwright 浏览器兜底读取。")
    p.add_argument("--allow-rule-fallback", action="store_true", help="当GPT未启用时，允许模糊候选按规则兜底通过。默认关闭，避免半信半疑内容进入报告。")
    p.add_argument("--progress-json", action="store_true", help="输出供桌面界面读取的结构化进度事件")
    p.add_argument("--task-state", type=Path, help="新任务的断点文件位置")
    p.add_argument("--resume-task", type=Path, help="恢复已有任务的断点文件")
    p.add_argument("--retry-mode", choices=("resume", "failed", "llm"), default="resume")
    p.add_argument("--test-model", action="store_true", help="用虚构样例测试真实模型调用，可能产生少量费用")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    if args.test_model:
        from gov_report.model_probe import run_probe
        print("@@GOV_MODEL_TEST " + json.dumps(run_probe(), ensure_ascii=False), flush=True)
        return
    with task_lock(args.resume_task or args.task_state):
        run_collection(args)


def run_collection(args) -> None:
    run_start_ts = time.perf_counter()
    def progress(payload):
        if args.progress_json:
            print("@@GOV_PROGRESS " + json.dumps(payload, ensure_ascii=False), flush=True)
    start, end = resolve_date_range(
        days=args.days,
        start_date=args.start_date,
        end_date=args.end_date,
        include_today=args.include_today,
    )
    sources = load_sources(args.sources)
    keywords = load_keywords(args.keywords)
    selected = [s for s in sources if not args.source or s["name"] == args.source]
    if args.source and not selected:
        raise ValueError("未找到指定站点")
    if args.resume_task and not args.resume_task.is_file():
        raise ValueError("任务断点文件不存在")
    if args.resume_task and args.task_state:
        raise ValueError("新建和恢复任务不能同时选择")
    if args.retry_mode != "resume" and not args.resume_task:
        raise ValueError("重试需要选择已有任务")
    state_path = args.resume_task or args.task_state
    prior = TaskState(state_path).get("meta", "", "task") if args.resume_task else None
    if args.resume_task and not prior:
        raise ValueError("任务文件缺少元数据，不能恢复")
    manual_urls = read_manual_urls(args.manual_urls)
    out_dir = Path(prior["output_dir"]) if prior else Path(args.output_root) / f"{start:%Y-%m-%d}_至_{end:%Y-%m-%d}" / ("task-" + uuid.uuid4().hex[:12])
    out_dir.mkdir(parents=True, exist_ok=True)
    state_path = state_path or out_dir / "task.sqlite3"
    metadata = dict(version=1, start_date=args.start_date or f"{start:%Y-%m-%d}", end_date=args.end_date or f"{end:%Y-%m-%d}",
                    sources=selected, keywords=keywords, strict=not args.loose, full_scan=args.full_scan,
                    allow_rule_fallback=args.allow_rule_fallback, use_llm=not args.no_llm,
                    max_channels=args.max_channels_per_source, max_detail=args.max_detail_per_source,
                    manual_urls=manual_urls, output_dir=str(out_dir.absolute()))
    task = TaskState(state_path, metadata)
    progress({"event": "task_ready", "path": str(state_path.absolute()), "summary": task.summary()})

    print(f"统计周期：{start:%Y-%m-%d %H:%M:%S} 至 {end:%Y-%m-%d %H:%M:%S}")
    print(f"输出目录：{out_dir}")

    crawler = GovCrawler(
        sources=sources,
        keywords=keywords,
        output_dir=out_dir,
        max_channels_per_source=args.max_channels_per_source,
        max_detail_per_source=args.max_detail_per_source,
        download_attachments=args.download_attachments,
        sleep=args.sleep,
        verify_ssl=not args.no_verify_ssl,
        strict=not args.loose,
        use_llm=not args.no_llm,
        browser_fallback=(args.browser_fallback and not args.no_browser_fallback),
        allow_rule_fallback=args.allow_rule_fallback,
        progress_callback=progress if args.progress_json else None,
        max_workers=args.workers,
        full_scan=args.full_scan,
        cache_dir=args.cache_dir or Path(args.output_root) / ".cache",
        use_cache=not args.no_cache,
        task_state=task,
    )

    if args.retry_mode == "llm":
        records = crawler.retry_model_failures(start, end)
    else:
        records = crawler.crawl(start, end, source_name=args.source)
    if manual_urls and args.retry_mode != "llm":
        progress({"event": "manual_started"})
        print(f"读取手工补充链接 {len(manual_urls)} 条")
        records.extend(crawler.crawl_manual_urls(manual_urls, start, end))
    records = task.records()
    coverage = task.summary()
    (out_dir / "coverage_summary.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2), encoding="utf-8")
    progress({"event": "coverage", "summary": coverage})

    # 再去重一次：同时按规范化URL、标题+日期+来源、正文hash去重。
    records = dedupe_records(records)
    records = sorted(records, key=lambda x: (x.get("publish_date", ""), x.get("source_name", "")), reverse=True)

    progress({"event": "export_started", "record_count": len(records)})
    export_start = time.perf_counter()
    paths = export_all(records, out_dir, start, end, keywords,
                       report_context={"coverage": coverage, "stages": crawler.metrics.snapshot()})
    export_seconds = time.perf_counter() - export_start
    progress({"event": "report_ready", "record_count": len(records), "paths": paths,
              "seconds": export_seconds})
    crawler.download_record_attachments(records)
    if args.download_attachments and paths.get("json"):
        Path(paths["json"]).write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
    crawler.write_log()

    elapsed = time.perf_counter() - run_start_ts
    elapsed_text = format_duration(elapsed)
    runtime_info = {
        "elapsed_seconds": round(elapsed, 3),
        "elapsed_text": elapsed_text,
        "record_count": len(records),
        "start_date": f"{start:%Y-%m-%d %H:%M:%S}",
        "end_date": f"{end:%Y-%m-%d %H:%M:%S}",
        "workers": args.workers,
        "full_scan": args.full_scan,
        "stages": crawler.metrics.snapshot(),
        "llm": crawler.llm_statistics(),
        "coverage": coverage,
        "export_seconds": round(export_seconds, 3),
    }
    (out_dir / "runtime_summary.json").write_text(json.dumps(runtime_info, ensure_ascii=False, indent=2), encoding="utf-8")
    with (out_dir / "crawl_log.txt").open("a", encoding="utf-8") as f:
        f.write(f"\n程序运行总时长：{elapsed_text}（{elapsed:.3f} 秒）\n")

    print("\n生成完成：")
    for k, v in paths.items():
        if v:
            print(f"- {k}: {v}")
        elif k == "pdf":
            print("- pdf: 未生成。请检查输出目录权限和软件字体文件，详见运行日志。")
    print(f"- log: {out_dir / 'crawl_log.txt'}")
    print(f"- runtime: {out_dir / 'runtime_summary.json'}")
    print(f"共命中 {len(records)} 条。")
    print(f"程序运行总时长：{elapsed_text}")
    print("大模型参数可在桌面界面中配置；命令行关闭复判可使用 --no-llm。")
    progress({"event": "completed", "record_count": len(records), "paths": paths,
              "elapsed_seconds": elapsed, "coverage": coverage})


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
