"""Production controller for the Qt Quick workspace."""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import queue
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import requests
import yaml
from PySide6.QtCore import QTimer, Slot
from PySide6.QtWidgets import QFileDialog

from ui_preview import APP_DIR, ROOT, Workspace


PROGRESS_PREFIX = "@@GOV_PROGRESS "
DEFAULTS = {
    "openai_base_url": "", "openai_api_key": "", "openai_model": "",
    "use_llm": True, "download_attachments": False, "browser_fallback": True,
    "strict_mode": True, "verify_ssl": True, "allow_rule_fallback": False,
    "sleep_seconds": 0.5, "reduced_motion": False, "reduced_transparency": False,
}


def settings_directory() -> Path:
    if os.getenv("GOV_REPORT_HOME"):
        return Path(os.environ["GOV_REPORT_HOME"]).expanduser()
    if sys.platform == "win32":
        return Path(os.getenv("APPDATA", str(Path.home()))) / "GovPolicyWeekly"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "GovPolicyWeekly"
    return Path(os.getenv("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "GovPolicyWeekly"


class SettingsStore:
    def __init__(self, path: Path | None = None, legacy: Path | None = None):
        self.path = path or settings_directory() / "user_settings.json"
        self.legacy = legacy if legacy is not None else APP_DIR / "user_settings.json"

    def load(self) -> dict:
        path = self.path if self.path.exists() else self.legacy
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, ValueError):
            return {}

    def save(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".settings-", suffix=".tmp", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump(data, handle, ensure_ascii=False, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)


def normalize_api_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc or parts.username or parts.password:
        raise ValueError("接口地址应为 http:// 或 https:// 开头的服务地址，不能包含账号密码")
    if parts.query or parts.fragment:
        raise ValueError("接口地址不能包含查询参数或片段，请填写服务的 API 根地址")
    path = parts.path.rstrip("/")
    for suffix in ("/chat/completions", "/responses", "/models"):
        if path.endswith(suffix):
            path = path[:-len(suffix)]
            break
    return urlunsplit((parts.scheme, parts.netloc, path, "", ""))


def fetch_model_catalogue(base_url: str, api_key: str, verify_ssl: bool) -> tuple[list[str], str]:
    base = normalize_api_url(base_url)
    if not api_key.strip():
        raise ValueError("请先填写 API Key")
    endpoints = [base + "/models"]
    if not urlsplit(base).path:
        endpoints.append(base + "/v1/models")
    for index, endpoint in enumerate(endpoints):
        response = requests.get(endpoint, headers={"Authorization": f"Bearer {api_key.strip()}"},
                                timeout=(10, 30), verify=verify_ssl)
        if response.status_code in (404, 405) and index + 1 < len(endpoints):
            continue
        if response.status_code in (401, 403):
            raise ValueError(f"服务返回 HTTP {response.status_code}，请检查密钥、接口地址及模型访问权限")
        response.raise_for_status()
        payload = response.json()
        values = payload.get("data", payload.get("models", [])) if isinstance(payload, dict) else payload
        if not isinstance(values, list):
            raise ValueError("接口返回的不是模型列表，请确认该服务支持 /models 接口")
        identifiers = set()
        for item in values:
            value = item.get("id") or item.get("name") if isinstance(item, dict) else item
            if isinstance(value, str) and value.strip():
                identifiers.add(value.strip())
        models = sorted(identifiers)
        if not models:
            raise ValueError("接口未返回可用模型，请检查账号权限或联系接口服务商")
        return models, endpoint[:-len("/models")]
    raise ValueError("未找到模型接口")


class DesktopController(Workspace):
    def __init__(self, sources, store: SettingsStore | None = None, resource_dir: Path = ROOT):
        super().__init__(sources)
        self.store = store or SettingsStore()
        self.resource_dir = resource_dir
        self.config = {**DEFAULTS, **self.store.load()}
        self.config["download_attachments"] = False
        default_output = Path.home() / "Documents" / "GovPolicyWeekly" / "output" if getattr(sys, "frozen", False) else APP_DIR / "output"
        self.config.setdefault("output_root", str(default_output))
        self._output = str(Path(self.config["output_root"]).expanduser().absolute())
        self._initial_settings = dict(self.config)
        models = self.config.get("model_options", [])
        self._model_options = [value for value in models if isinstance(value, str)] if isinstance(models, list) else []
        selected_model = self.config.get("openai_model", "")
        if selected_model and selected_model not in self._model_options:
            self._model_options.append(selected_model)
        selected = self.config.get("selected_sources")
        if isinstance(selected, list):
            for row in sources.rows:
                row["selected"] = row["siteName"] in selected
        self.events = queue.Queue()
        self.process = None
        self._reader = None
        self._run_id = None
        self._started_at = None
        self._stopping = False
        self._models_loading = False
        self._closing = False
        self._closed = False
        self._model_request = 0
        self._scan_request = 0
        self._last_pdf = ""
        self._completed_payload = None
        self._errors = 0
        self._known_secrets = {self.config.get("openai_api_key", "")}
        self._pending_model = None
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._drain)
        self.timer.start()
        self.add_log("READY", "采集工作台已就绪")
        self.add_log("INFO", f"已载入 {sources.total} 个站点；政策与人事核心栏目，最多三站并行")
        self.add_log("INFO", "PDF 可由内置引擎生成，不依赖 LibreOffice")
        self.refreshReports()

    def add_log(self, level, message):
        for secret in getattr(self, "_known_secrets", ()):
            if secret:
                message = str(message).replace(secret, "[已隐藏密钥]")
        super().add_log(level, message)

    def _options(self, options):
        data = dict(options)
        result = dict(self.config)
        for key, default in DEFAULTS.items():
            if key not in data:
                continue
            if isinstance(default, bool):
                result[key] = bool(data[key])
            elif key == "sleep_seconds":
                value = float(data[key])
                if not math.isfinite(value) or not 0 <= value <= 60:
                    raise ValueError("请求间隔应在 0 到 60 秒之间")
                result[key] = value
            else:
                result[key] = str(data[key]).strip()
        for key in ("start_date", "end_date"):
            if key in data:
                result[key] = str(data[key])
        result["output_root"] = self._output
        result["model_options"] = list(self._model_options)
        result["selected_sources"] = [row["siteName"] for row in self.sources.rows if row["selected"]]
        return result

    @Slot("QVariantMap")
    def saveConfig(self, options):
        try:
            updated = self._options(options)
            self._known_secrets.add(updated.get("openai_api_key", ""))
            if updated != self.config or not self.store.path.exists():
                self.store.save(updated)
                self.config = updated
        except (OSError, ValueError, TypeError) as error:
            self.add_log("ERROR", f"配置保存失败：{error}")
            self.toast.emit("配置未能保存，请检查用户目录的写入权限")

    @Slot(str, str, bool)
    def fetchModels(self, base_url, api_key, verify_ssl=True):
        if self._models_loading or self._running:
            return
        try:
            normalize_api_url(base_url)
            if not api_key.strip():
                raise ValueError("请先填写 API Key")
        except ValueError as error:
            self.toast.emit(str(error))
            return
        self._known_secrets.add(api_key.strip())
        self._model_request += 1
        request = self._model_request
        self._models_loading = True
        self._pending_model = (base_url.strip(), api_key.strip())
        self.modelsChanged.emit()

        def work():
            try:
                catalogue = fetch_model_catalogue(base_url, api_key, verify_ssl)
                self.events.put(("models", request, catalogue))
            except Exception as error:
                self.events.put(("model_error", request, str(error)))
        threading.Thread(target=work, daemon=True).start()

    @Slot()
    def chooseOutput(self):
        if self._running:
            return
        folder = QFileDialog.getExistingDirectory(None, "选择输出目录", self._output)
        if folder:
            self._output = folder
            self.saveConfig({})
            self.changed.emit()
            self.refreshReports()

    @Slot()
    def refreshReports(self):
        self._scan_request += 1
        request = self._scan_request
        output = Path(self._output)
        def scan():
            rows = []
            try:
                for path in output.rglob("*.pdf") if output.is_dir() else []:
                    try:
                        stat = path.stat()
                        rows.append(dict(reportName=path.stem, reportPath=str(path),
                                         reportDate=dt.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M"),
                                         reportSize=f"{stat.st_size / 1024:.0f} KB", modified=stat.st_mtime))
                    except OSError:
                        continue
                rows.sort(key=lambda row: row["modified"], reverse=True)
                self.events.put(("reports", request, rows))
            except OSError as error:
                self.events.put(("report_error", request, str(error)))
        threading.Thread(target=scan, daemon=True).start()

    @Slot(str, str, "QVariantMap")
    def start(self, start_date, end_date, options=None):
        if self._running or self._models_loading:
            return
        try:
            start = dt.date.fromisoformat(start_date)
            end = dt.date.fromisoformat(end_date)
            if start > end:
                raise ValueError("开始日期不能晚于结束日期")
            config = self._options(options or {})
            selected = [row for row in self.sources.rows if row["selected"]]
            if not selected:
                raise ValueError("请至少选择一个采集站点")
            if config["use_llm"]:
                config["openai_base_url"] = normalize_api_url(config["openai_base_url"])
                if not config["openai_api_key"]:
                    raise ValueError("请填写 API Key，或关闭大模型后按规则运行")
                if not config["openai_model"]:
                    raise ValueError("请先获取并选择一个模型")
            run_id = uuid.uuid4().hex
            run_dir = self.store.path.parent / "runtime" / run_id
            run_dir.mkdir(parents=True)
            names = {row["siteName"] for row in selected}
            source_path = run_dir / "sources.yaml"
            source_path.write_text(yaml.safe_dump([row for row in self.sources.source_data if row["name"] in names],
                                                  allow_unicode=True, sort_keys=False), encoding="utf-8")
            out_root = Path(self._output)
            out_root.mkdir(parents=True, exist_ok=True)
            self.saveConfig({**config, "start_date": start_date, "end_date": end_date})
            command = [sys.executable]
            command += ["--run-cli"] if getattr(sys, "frozen", False) else ["-u", str(ROOT / "main.py")]
            command += ["--start-date", start_date, "--end-date", end_date, "--output-root", str(out_root),
                        "--sources", str(source_path), "--keywords", str(self.resource_dir / "config" / "keywords.yaml"),
                        "--manual-urls", str(self.resource_dir / "input" / "manual_urls.txt"),
                        "--max-channels-per-source", "0", "--max-detail-per-source", "0",
                        "--sleep", str(config["sleep_seconds"]), "--progress-json"]
            if config["download_attachments"]:
                command.append("--download-attachments")
            for key, flag in (("use_llm", "--no-llm"), ("download_attachments", "--no-download-attachments"),
                              ("browser_fallback", "--no-browser-fallback"), ("strict_mode", "--loose"),
                              ("verify_ssl", "--no-verify-ssl")):
                if not config[key]:
                    command.append(flag)
            if config["allow_rule_fallback"]:
                command.append("--allow-rule-fallback")
            environment = os.environ.copy()
            environment.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1",
                               GOV_REPORT_OPENAI_API_KEY=config["openai_api_key"],
                               GOV_REPORT_OPENAI_BASE_URL=config["openai_base_url"],
                               GOV_REPORT_OPENAI_MODEL=config["openai_model"])
            environment.pop("GOV_REPORT_WORKER_LOG", None)
            worker_log = None
            if getattr(sys, "frozen", False):
                worker_log = run_dir / "worker.log"
                worker_log.touch()
                environment["GOV_REPORT_WORKER_LOG"] = str(worker_log)
            process = subprocess.Popen(command, cwd=APP_DIR, env=environment,
                                       stdout=subprocess.DEVNULL if worker_log else subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace",
                                       start_new_session=os.name != "nt",
                                       creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == "nt" else 0)
        except (ValueError, OSError, TypeError) as error:
            self.add_log("ERROR", f"无法启动：{error}")
            self.toast.emit(str(error))
            return
        self.process = process
        self._run_id = run_id
        self._active = selected
        self._running = True
        self._stopping = False
        self._state = "采集中"
        self._current = selected[0]["siteName"]
        self._phase = "准备采集"
        self._done = self._pages = self._hits = self._errors = 0
        self._stage_stats = {}
        self._active_sources = {}
        self._current_column = ""
        self._completed_payload = None
        self._last_pdf = ""
        self._started_at = time.monotonic()
        self._elapsed_seconds = 0
        self.add_log("START", f"任务开始  {start_date} 至 {end_date} · {len(selected)} 个站点")
        self.changed.emit()
        self._reader = threading.Thread(target=self._read_worker, args=(process, run_id, worker_log), daemon=True)
        self._reader.start()

    def _read_worker(self, process, run_id, worker_log):
        try:
            if worker_log:
                with worker_log.open(encoding="utf-8", errors="replace") as stream:
                    while True:
                        line = stream.readline()
                        if line:
                            self.events.put(("line", run_id, line))
                        elif process.poll() is not None:
                            for line in stream.read().splitlines():
                                self.events.put(("line", run_id, line))
                            break
                        else:
                            time.sleep(0.05)
            else:
                for line in process.stdout:
                    self.events.put(("line", run_id, line))
        except Exception as error:
            self.events.put(("line", run_id, f"读取任务日志失败：{error}"))
        finally:
            if process.stdout:
                process.stdout.close()
            self.events.put(("finished", run_id, process.wait()))

    def _progress(self, event):
        kind = event.get("event")
        if kind == "source_started":
            self._current = str(event.get("source", ""))
            self._phase = "栏目与列表"
            self._active_sources[self._current] = self._phase
        elif kind == "page_processed":
            self._pages += 1
            self._phase = "详情提取" if event.get("kind") == "detail" else "栏目与列表"
        elif kind == "stage_started":
            labels = {"list": "栏目与列表", "detail": "详情提取", "llm": "模型判断", "attachment": "附件下载"}
            self._phase = labels.get(event.get("kind"), "采集中")
            self._current = str(event.get("source", self._current))
            self._current_column = str(event.get("column") or event.get("url") or "")
            if self._current:
                self._active_sources[self._current] = self._phase
        elif kind == "stage_finished":
            stage = self._stage_stats.setdefault(event.get("kind"), {"count": 0, "seconds": 0, "cache_hits": 0, "errors": 0})
            stage["count"] += 1
            stage["seconds"] += max(0, float(event.get("seconds", 0)))
            stage["cache_hits"] += int(bool(event.get("cache_hit")))
            stage["errors"] += int(bool(event.get("error")))
        elif kind == "record_included":
            self._hits += 1
            self._phase = "分类与汇总"
        elif kind == "source_finished":
            self._done += 1
            self._active_sources.pop(str(event.get("source", "")), None)
        elif kind == "error":
            self._errors += 1
        elif kind == "export_started":
            self._state = "生成报告中"
            self._phase = "PDF 报告"
            self._hits = int(event.get("record_count", self._hits))
        elif kind == "manual_started":
            self._current = "手工补充链接"
            self._phase = "详情提取"
        elif kind == "report_ready":
            pdf = Path(event.get("paths", {}).get("pdf", ""))
            if pdf.is_file() and pdf.suffix.lower() == ".pdf":
                self._last_pdf = str(pdf.absolute())
                self.add_log("DONE", "PDF 已生成，可立即打开")
                self.refreshReports()
        elif kind == "attachments_started":
            self._state = "PDF 已生成，下载附件中"
            self._phase = "附件下载"
        elif kind == "completed":
            self._completed_payload = event
            self._hits = int(event.get("record_count", self._hits))
        self.changed.emit()

    def _drain(self):
        for _ in range(200):
            try:
                kind, token, value = self.events.get_nowait()
            except queue.Empty:
                break
            if kind in {"line", "finished"} and token == self._run_id:
                if kind == "finished":
                    self._finish(value)
                else:
                    text = value.rstrip("\r\n")
                    if text.startswith(PROGRESS_PREFIX):
                        try:
                            payload = json.loads(text[len(PROGRESS_PREFIX):])
                            if isinstance(payload, dict):
                                self._progress(payload)
                        except (ValueError, TypeError):
                            self.add_log("WARN", "忽略一条无法解析的进度事件")
                    elif text:
                        self.add_log("ERROR" if "[ERROR]" in text or "失败:" in text else "INFO", text)
            elif kind in {"models", "model_error"} and token == self._model_request:
                self._models_loading = False
                current = (self.config.get("openai_base_url", ""), self.config.get("openai_api_key", ""))
                if self._pending_model != current:
                    self.toast.emit("接口配置已改变，请重新获取模型")
                elif kind == "models":
                    models, base_url = value
                    self._model_options = models
                    self.apiBaseResolved.emit(base_url)
                    self.saveConfig({"openai_base_url": base_url})
                    self.add_log("INFO", f"已获取 {len(models)} 个模型")
                    self.toast.emit(f"已获取 {len(models)} 个模型")
                else:
                    self.add_log("ERROR", f"获取模型失败：{value}")
                    self.toast.emit("获取模型失败，详情见运行日志")
                self.modelsChanged.emit()
            elif kind == "reports" and token == self._scan_request:
                self.reports.replace(value)
            elif kind == "report_error" and token == self._scan_request:
                self.add_log("WARN", f"报告列表读取失败：{value}")
        if self._running:
            seconds = time.monotonic() - self._started_at
            if int(seconds) != int(self._elapsed_seconds):
                self._elapsed_seconds = seconds
                self.changed.emit()

    def _finish(self, code):
        was_stopping = self._stopping
        self._elapsed_seconds = time.monotonic() - self._started_at
        self._running = False
        self._active_sources = {}
        self._stopping = False
        payload = self._completed_payload or {}
        pdf = Path(payload.get("paths", {}).get("pdf", ""))
        if was_stopping:
            self._state = "已停止"
            self._phase = "任务已停止"
            self.add_log("STOP", "任务已停止，未完成的报告不会标记为成功")
        elif code == 0 and pdf.is_file() and pdf.suffix.lower() == ".pdf":
            self._state = "已完成（有警告）" if self._errors else "已完成"
            self._phase = "报告已生成"
            self._last_pdf = str(pdf.absolute())
            self.add_log("DONE", f"已生成 PDF：{self._last_pdf}")
            self.toast.emit("PDF 报告已生成")
            self.refreshReports()
        else:
            self._state = "任务失败"
            self._phase = "请查看运行日志"
            self.add_log("ERROR", f"任务未成功生成 PDF，退出码：{code}")
            self.toast.emit("任务未完成，详情见运行日志")
        self.changed.emit()
        if self._closing:
            self.closeReady.emit()

    def _signal_process(self, force=False):
        process = self.process
        if not process or process.poll() is not None:
            return
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
            else:
                os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
        except (OSError, subprocess.TimeoutExpired):
            if process.poll() is None:
                process.kill()

    @Slot()
    def stop(self):
        if not self._running or self._stopping:
            return
        self._stopping = True
        self._state = "正在停止"
        self.add_log("STOP", "正在停止采集及其浏览器子进程")
        self.changed.emit()
        threading.Thread(target=self._signal_process, daemon=True).start()
        token = self._run_id
        QTimer.singleShot(5000, lambda: self._signal_process(True) if self._running and self._run_id == token else None)

    @Slot()
    def requestExit(self):
        self._closing = True
        if self._running:
            self.stop()
        else:
            self.closeReady.emit()

    def shutdown(self):
        self._closed = True
        self.timer.stop()
        self._signal_process(True)
        if self.process and self.process.poll() is None:
            self.process.wait(timeout=10)
        if self._reader:
            self._reader.join(timeout=2)
