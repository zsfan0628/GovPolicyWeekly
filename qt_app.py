from __future__ import annotations

import datetime as dt
import json
import os
import queue
import subprocess
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path
from urllib.parse import urljoin

import requests
import yaml
from PySide6.QtCore import QDate, Qt, QTimer, Signal
from PySide6.QtGui import QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
SETTINGS_PATH = APP_DIR / "user_settings.json"
RUNTIME_DIR = APP_DIR / ".app_runtime"
NO_LIMIT_VALUE = "0"


class GovPolicyQtApp(QWidget):
    models_ready = Signal(list, str)
    models_failed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("政府政策周报生成工具")
        self.resize(1080, 820)

        self.process: subprocess.Popen | None = None
        self.log_queue: queue.Queue[object] = queue.Queue()
        self.source_data: list[dict] = []
        self.source_names: list[str] = []
        self.syncing_sources = False
        self.last_output_dir: Path | None = None

        self.settings = self._load_settings()
        self._build_ui()
        self._load_sources()
        self._restore_settings()

        self.models_ready.connect(self._apply_models)
        self.models_failed.connect(self._model_error)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._drain_log_queue)
        self.timer.start(100)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        date_group = QGroupBox("基础设置")
        date_layout = QGridLayout(date_group)
        today = dt.date.today()
        default_end = today - dt.timedelta(days=1)
        default_start = default_end - dt.timedelta(days=6)
        self.start_date = QDateEdit(QDate(default_start.year, default_start.month, default_start.day))
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy-MM-dd")
        self.end_date = QDateEdit(QDate(default_end.year, default_end.month, default_end.day))
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy-MM-dd")
        self.output_root = QLineEdit(str(APP_DIR / "output"))
        choose_output = QPushButton("选择")
        choose_output.clicked.connect(self._choose_output)
        recent7 = QPushButton("最近7天")
        recent7.clicked.connect(lambda: self._set_recent_days(7))
        recent30 = QPushButton("最近30天")
        recent30.clicked.connect(lambda: self._set_recent_days(30))

        date_layout.addWidget(QLabel("开始日期"), 0, 0)
        date_layout.addWidget(self.start_date, 0, 1)
        date_layout.addWidget(QLabel("结束日期"), 0, 2)
        date_layout.addWidget(self.end_date, 0, 3)
        date_layout.addWidget(recent7, 0, 4)
        date_layout.addWidget(recent30, 0, 5)
        date_layout.addWidget(QLabel("输出目录"), 1, 0)
        date_layout.addWidget(self.output_root, 1, 1, 1, 4)
        date_layout.addWidget(choose_output, 1, 5)
        root.addWidget(date_group)

        llm_group = QGroupBox("大模型配置")
        llm_layout = QGridLayout(llm_group)
        self.use_llm = QCheckBox("启用 GPT 复判")
        self.use_llm.setChecked(True)
        self.api_url = QLineEdit()
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.model_box = QComboBox()
        self.model_box.setEditable(False)
        self.fetch_models = QPushButton("获取模型")
        self.fetch_models.clicked.connect(self._fetch_models)
        llm_layout.addWidget(self.use_llm, 0, 0)
        llm_layout.addWidget(QLabel("API URL"), 1, 0)
        llm_layout.addWidget(self.api_url, 1, 1, 1, 4)
        llm_layout.addWidget(QLabel("API Key"), 2, 0)
        llm_layout.addWidget(self.api_key, 2, 1, 1, 3)
        llm_layout.addWidget(self.fetch_models, 2, 4)
        llm_layout.addWidget(QLabel("模型"), 3, 0)
        llm_layout.addWidget(self.model_box, 3, 1)
        root.addWidget(llm_group)

        run_group = QGroupBox("运行设置")
        run_layout = QGridLayout(run_group)
        self.download_attachments = QCheckBox("下载附件")
        self.download_attachments.setChecked(False)
        self.browser_fallback = QCheckBox("浏览器兜底")
        self.browser_fallback.setChecked(True)
        self.strict_mode = QCheckBox("严格模式")
        self.strict_mode.setChecked(True)
        self.verify_ssl = QCheckBox("校验 SSL")
        self.verify_ssl.setChecked(True)
        self.allow_rule_fallback = QCheckBox("规则兜底")
        self.sleep_seconds = QSpinBox()
        self.sleep_seconds.setRange(0, 10)
        self.sleep_seconds.setValue(0)
        self.sleep_decimal = QLineEdit("0.5")
        run_layout.addWidget(self.download_attachments, 0, 0)
        run_layout.addWidget(self.browser_fallback, 0, 1)
        run_layout.addWidget(self.strict_mode, 0, 2)
        run_layout.addWidget(self.verify_ssl, 0, 3)
        run_layout.addWidget(self.allow_rule_fallback, 0, 4)
        run_layout.addWidget(QLabel("请求间隔秒"), 1, 0)
        run_layout.addWidget(self.sleep_decimal, 1, 1)
        root.addWidget(run_group)

        source_group = QGroupBox("采集站点")
        source_layout = QVBoxLayout(source_group)
        self.select_all_sources = QCheckBox("全部站点")
        self.select_all_sources.setChecked(True)
        self.select_all_sources.stateChanged.connect(self._toggle_all_sources)
        self.source_list = QListWidget()
        self.source_list.setMaximumHeight(180)
        self.source_list.itemChanged.connect(self._sync_select_all_sources)
        source_layout.addWidget(self.select_all_sources)
        source_layout.addWidget(self.source_list)
        root.addWidget(source_group)

        actions = QHBoxLayout()
        self.run_button = QPushButton("开始生成")
        self.run_button.clicked.connect(self._start_run)
        self.stop_button = QPushButton("停止")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self._stop_run)
        open_output = QPushButton("打开输出目录")
        open_output.clicked.connect(lambda: self._open_path(Path(self.output_root.text())))
        open_last = QPushButton("打开本次结果")
        open_last.clicked.connect(self._open_last_output)
        clear_log = QPushButton("清空日志")
        clear_log.clicked.connect(self._clear_log)
        actions.addWidget(self.run_button)
        actions.addWidget(self.stop_button)
        actions.addWidget(open_output)
        actions.addWidget(open_last)
        actions.addWidget(clear_log)
        actions.addStretch(1)
        root.addLayout(actions)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        root.addWidget(self.log_text, 1)

    def _restore_settings(self) -> None:
        s = self.settings
        self.output_root.setText(s.get("output_root", self.output_root.text()))
        self.api_url.setText(s.get("openai_base_url", ""))
        self.api_key.setText(s.get("openai_api_key", ""))
        models = s.get("model_options", [])
        if models:
            self.model_box.addItems(models)
        model = s.get("openai_model", "")
        if model and self.model_box.findText(model) < 0:
            self.model_box.addItem(model)
        if model:
            self.model_box.setCurrentText(model)

    def _load_sources(self) -> None:
        path = RESOURCE_DIR / "config" / "sources.yaml"
        self.source_data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
        self.source_names = [str(item["name"]) for item in self.source_data if item.get("name")]
        selected = set(self.settings.get("selected_sources", self.source_names))
        for name in self.source_names:
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if name in selected else Qt.Unchecked)
            self.source_list.addItem(item)
        self._sync_select_all_sources()
        self._append_log(f"已加载采集站点：{len(self.source_names)} 个\n")

    def _selected_sources(self) -> list[str]:
        out = []
        for i in range(self.source_list.count()):
            item = self.source_list.item(i)
            if item.checkState() == Qt.Checked:
                out.append(item.text())
        return out

    def _toggle_all_sources(self, *_args) -> None:
        if self.syncing_sources:
            return
        self.syncing_sources = True
        state = Qt.Checked if self.select_all_sources.isChecked() else Qt.Unchecked
        for i in range(self.source_list.count()):
            self.source_list.item(i).setCheckState(state)
        self.syncing_sources = False

    def _sync_select_all_sources(self, *_args) -> None:
        if self.syncing_sources:
            return
        total = self.source_list.count()
        checked = len(self._selected_sources())
        self.syncing_sources = True
        self.select_all_sources.setChecked(bool(total) and checked == total)
        self.syncing_sources = False

    def _choose_output(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", self.output_root.text())
        if path:
            self.output_root.setText(path)

    def _set_recent_days(self, days: int) -> None:
        end = dt.date.today() - dt.timedelta(days=1)
        start = end - dt.timedelta(days=days - 1)
        self.start_date.setDate(QDate(start.year, start.month, start.day))
        self.end_date.setDate(QDate(end.year, end.month, end.day))

    def _fetch_models(self) -> None:
        base_url = self.api_url.text().strip()
        api_key = self.api_key.text().strip()
        if not base_url or not api_key:
            QMessageBox.warning(self, "参数错误", "请先填写 API URL 和 API Key")
            return
        self.fetch_models.setEnabled(False)
        threading.Thread(target=self._fetch_models_worker, args=(base_url, api_key), daemon=True).start()

    def _fetch_models_worker(self, base_url: str, api_key: str) -> None:
        try:
            url = urljoin(base_url.rstrip("/") + "/", "models")
            resp = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            models = sorted({str(item["id"]) for item in data.get("data", []) if isinstance(item, dict) and item.get("id")})
            if not models:
                raise RuntimeError("没有找到模型 id")
            self.models_ready.emit(models, url)
        except Exception as exc:
            self.models_failed.emit(str(exc))

    def _apply_models(self, models: list[str], url: str) -> None:
        self.model_box.clear()
        self.model_box.addItems(models)
        self.fetch_models.setEnabled(True)
        self._append_log(f">>> 已从 {url} 获取 {len(models)} 个模型\n")
        self._save_settings()

    def _model_error(self, error: str) -> None:
        self.fetch_models.setEnabled(True)
        self._append_log(f">>> 获取模型失败：{error}\n")

    def _start_run(self) -> None:
        if self.process and self.process.poll() is None:
            return
        selected_sources = self._selected_sources()
        if not selected_sources:
            QMessageBox.warning(self, "参数错误", "请至少选择一个采集站点")
            return
        start = self.start_date.date().toPython()
        end = self.end_date.date().toPython()
        out_root = Path(self.output_root.text()).expanduser()
        self.last_output_dir = out_root / f"{start:%Y-%m-%d}_至_{end:%Y-%m-%d}"
        sources_path = self._write_runtime_sources(selected_sources)
        self._save_settings()
        cmd = [sys.executable]
        if getattr(sys, "frozen", False):
            cmd.append("--run-cli")
        else:
            cmd.extend(["-u", str(APP_DIR / "main.py")])
        cmd.extend([
            "--start-date", f"{start:%Y-%m-%d}",
            "--end-date", f"{end:%Y-%m-%d}",
            "--output-root", str(out_root),
            "--sources", str(sources_path),
            "--keywords", str(RESOURCE_DIR / "config" / "keywords.yaml"),
            "--manual-urls", str(RESOURCE_DIR / "input" / "manual_urls.txt"),
            "--max-channels-per-source", NO_LIMIT_VALUE,
            "--max-detail-per-source", NO_LIMIT_VALUE,
            "--sleep", self.sleep_decimal.text().strip() or "0.5",
        ])
        if not self.use_llm.isChecked():
            cmd.append("--no-llm")
        if not self.download_attachments.isChecked():
            cmd.append("--no-download-attachments")
        else:
            cmd.append("--download-attachments")
        if not self.browser_fallback.isChecked():
            cmd.append("--no-browser-fallback")
        if not self.strict_mode.isChecked():
            cmd.append("--loose")
        if not self.verify_ssl.isChecked():
            cmd.append("--no-verify-ssl")
        if self.allow_rule_fallback.isChecked():
            cmd.append("--allow-rule-fallback")

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        worker_log = None
        if getattr(sys, "frozen", False):
            worker_log = RUNTIME_DIR / f"worker-{uuid.uuid4().hex}.log"
            worker_log.touch()
            env["GOV_REPORT_WORKER_LOG"] = str(worker_log)
        if self.api_key.text().strip():
            env["GOV_REPORT_OPENAI_API_KEY"] = self.api_key.text().strip()
        if self.api_url.text().strip():
            env["GOV_REPORT_OPENAI_BASE_URL"] = self.api_url.text().strip()
        if self.model_box.currentText().strip():
            env["GOV_REPORT_OPENAI_MODEL"] = self.model_box.currentText().strip()

        self._append_log("\n>>> 启动任务\n")
        self.process = subprocess.Popen(
            cmd, cwd=str(APP_DIR),
            stdout=subprocess.DEVNULL if worker_log else subprocess.PIPE,
            stderr=subprocess.STDOUT, text=False, env=env,
        )
        self.run_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        threading.Thread(target=self._read_process_output, args=(self.process, worker_log), daemon=True).start()

    def _read_process_output(self, process: subprocess.Popen, worker_log: Path | None = None) -> None:
        if worker_log:
            # Windowed executables have no Python stdout, even with a parent pipe.
            with worker_log.open(encoding="utf-8", errors="replace") as stream:
                while True:
                    line = stream.readline()
                    if line:
                        self.log_queue.put(line)
                    elif process.poll() is not None:
                        self.log_queue.put(stream.read())
                        break
                    else:
                        time.sleep(0.1)
        else:
            assert process.stdout
            for line in process.stdout:
                self.log_queue.put(self._decode_process_line(line))
        code = process.wait()
        if worker_log and code == 0:
            worker_log.unlink(missing_ok=True)
        self.log_queue.put(f"\n>>> 任务结束，退出码：{code}\n")
        self.log_queue.put("__DONE__")

    def _drain_log_queue(self) -> None:
        while True:
            try:
                item = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if item == "__DONE__":
                self.run_button.setEnabled(True)
                self.stop_button.setEnabled(False)
            else:
                self._append_log(str(item))

    def _stop_run(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()

    def _write_runtime_sources(self, selected_sources: list[str]) -> Path:
        RUNTIME_DIR.mkdir(exist_ok=True)
        selected = set(selected_sources)
        data = [item for item in self.source_data if str(item.get("name")) in selected]
        path = RUNTIME_DIR / "selected_sources.yaml"
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        return path

    def _save_settings(self) -> None:
        data = {
            "output_root": self.output_root.text(),
            "openai_base_url": self.api_url.text(),
            "openai_api_key": self.api_key.text(),
            "openai_model": self.model_box.currentText(),
            "model_options": [self.model_box.itemText(i) for i in range(self.model_box.count())],
            "selected_sources": self._selected_sources(),
        }
        SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load_settings(self) -> dict:
        if SETTINGS_PATH.exists():
            try:
                return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _append_log(self, text: str) -> None:
        scroll_bar = self.log_text.verticalScrollBar()
        should_follow = scroll_bar.value() >= scroll_bar.maximum() - 4
        cursor = QTextCursor(self.log_text.document())
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        if should_follow:
            scroll_bar.setValue(scroll_bar.maximum())

    def _clear_log(self) -> None:
        self.log_text.clear()

    def _open_last_output(self) -> None:
        if self.last_output_dir:
            self._open_path(self.last_output_dir)

    def _open_path(self, path: Path) -> None:
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            subprocess.Popen(["open", str(path)])

    @staticmethod
    def _decode_process_line(line: bytes) -> str:
        for enc in ("utf-8", "gb18030", "cp936"):
            try:
                return line.decode(enc)
            except Exception:
                pass
        return line.decode("utf-8", errors="replace")


def run_cli_from_frozen() -> None:
    log_path = os.getenv("GOV_REPORT_WORKER_LOG")
    if log_path:
        sys.stdout = sys.stderr = open(log_path, "w", encoding="utf-8", buffering=1)
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    try:
        from main import main

        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--self-test":
        from gov_report.self_test import run_self_test

        sys.exit(run_self_test(Path(sys.argv[2])))
    elif "--run-cli" in sys.argv:
        sys.argv.remove("--run-cli")
        run_cli_from_frozen()
    else:
        app = QApplication(sys.argv)
        window = GovPolicyQtApp()
        window.show()
        sys.exit(app.exec())
