from __future__ import annotations

import calendar
import datetime as dt
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urljoin
from tkinter import BooleanVar, END, Listbox, StringVar, Text, Tk, Toplevel, filedialog, messagebox
from tkinter import ttk
import tkinter as tk

import requests

try:
    import yaml
except ImportError:  # pragma: no cover - only used when dependencies are incomplete.
    yaml = None


APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR))
DEFAULT_OUTPUT_ROOT = APP_DIR / "output"
SETTINGS_PATH = APP_DIR / "user_settings.json"
RUNTIME_DIR = APP_DIR / ".app_runtime"
NO_LIMIT_VALUE = "0"


class DatePicker(Toplevel):
    def __init__(self, parent: Tk, target_var: StringVar, anchor_widget, on_close=None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.anchor_widget = anchor_widget
        self.on_close = on_close
        self.parent_click_binding: str | None = None
        self.overrideredirect(True)
        self.transient(parent)
        self.resizable(False, False)
        self.configure(background="#f7f7f7", borderwidth=1, relief="solid")
        self.target_var = target_var

        try:
            current = dt.datetime.strptime(target_var.get(), "%Y-%m-%d").date()
        except ValueError:
            current = dt.date.today()

        self.year = current.year
        self.month = current.month
        self.selected = current

        self.header = ttk.Frame(self, padding=(8, 8, 8, 6))
        self.header.grid(row=0, column=0, sticky="ew")
        ttk.Button(self.header, text="<<", width=3, command=self._prev_year).grid(row=0, column=0)
        ttk.Button(self.header, text="<", width=3, command=self._prev_month).grid(row=0, column=1, padx=(4, 0))
        self.title_var = StringVar()
        ttk.Label(self.header, textvariable=self.title_var, width=14, anchor="center", font=("", 14, "bold")).grid(row=0, column=2, padx=8)
        ttk.Button(self.header, text=">", width=3, command=self._next_month).grid(row=0, column=3, padx=(0, 4))
        ttk.Button(self.header, text=">>", width=3, command=self._next_year).grid(row=0, column=4)

        self.body = tk.Frame(self, background="#f7f7f7", padx=8, pady=4)
        self.body.grid(row=1, column=0)
        footer = ttk.Frame(self, padding=(8, 4, 8, 8))
        footer.grid(row=2, column=0, sticky="ew")
        ttk.Button(footer, text="今天", command=lambda: self._choose(dt.date.today())).pack(fill="x")

        self._render()
        self.update_idletasks()
        x = anchor_widget.winfo_rootx()
        y = anchor_widget.winfo_rooty() + anchor_widget.winfo_height() + 2
        self.geometry(f"+{x}+{y}")
        self.bind("<Escape>", lambda _event: self.destroy())
        self.after(120, self._bind_parent_click)

    def _bind_parent_click(self) -> None:
        self.parent_click_binding = self.parent.bind("<Button-1>", self._close_from_parent_click, add="+")

    def _close_from_parent_click(self, _event) -> None:
        x = self.anchor_widget.winfo_rootx()
        y = self.anchor_widget.winfo_rooty()
        width = self.anchor_widget.winfo_width()
        height = self.anchor_widget.winfo_height()
        pointer_x = self.parent.winfo_pointerx()
        pointer_y = self.parent.winfo_pointery()
        if x <= pointer_x <= x + width and y <= pointer_y <= y + height:
            return
        if self.winfo_exists():
            self.destroy()

    def destroy(self) -> None:
        if self.parent_click_binding:
            try:
                self.parent.unbind("<Button-1>", self.parent_click_binding)
            except Exception:
                pass
            self.parent_click_binding = None
        if self.on_close:
            self.on_close(self)
        super().destroy()

    def _render(self) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        self.title_var.set(f"{self.year}年  {self.month}月")

        weekdays = ["一", "二", "三", "四", "五", "六", "日"]
        for col, label in enumerate(weekdays):
            tk.Label(
                self.body,
                text=label,
                width=4,
                height=1,
                anchor="center",
                background="#f7f7f7",
                foreground="#222222",
                font=("", 13, "bold"),
            ).grid(row=0, column=col, padx=2, pady=(0, 6))

        month_days = calendar.Calendar(firstweekday=0).monthdatescalendar(self.year, self.month)
        for row, week in enumerate(month_days, start=1):
            for col, day in enumerate(week):
                is_current_month = day.month == self.month
                is_selected = day == self.selected
                label = tk.Label(
                    self.body,
                    text=str(day.day),
                    width=4,
                    height=1,
                    anchor="center",
                    cursor="hand2",
                    background="#e9e9e9" if is_selected else "#f7f7f7",
                    foreground="#222222" if is_current_month else "#8d8d8d",
                    font=("", 14),
                    relief="solid" if is_selected else "flat",
                    borderwidth=1 if is_selected else 0,
                )
                label.grid(row=row, column=col, padx=4, pady=4)
                label.bind("<Button-1>", lambda _event, picked=day: self._choose(picked))
                label.bind("<Enter>", lambda _event, widget=label: widget.configure(background="#ededed"))
                label.bind("<Leave>", lambda _event, widget=label, selected=is_selected: widget.configure(background="#e9e9e9" if selected else "#f7f7f7"))

    def _choose(self, picked: dt.date) -> None:
        self.target_var.set(picked.strftime("%Y-%m-%d"))
        self.destroy()

    def _prev_month(self) -> None:
        if self.month == 1:
            self.year -= 1
            self.month = 12
        else:
            self.month -= 1
        self._render()

    def _next_month(self) -> None:
        if self.month == 12:
            self.year += 1
            self.month = 1
        else:
            self.month += 1
        self._render()

    def _prev_year(self) -> None:
        self.year -= 1
        self._render()

    def _next_year(self) -> None:
        self.year += 1
        self._render()


class ScrollableChecks(ttk.Frame):
    def __init__(self, parent: ttk.Frame, on_change=None) -> None:
        super().__init__(parent)
        self.names: list[str] = []
        self.selected: set[str] = set()
        self.on_change = on_change
        self.listbox = Listbox(self, height=8, activestyle="dotbox", exportselection=False)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scrollbar.set)
        self.listbox.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.listbox.bind("<ButtonRelease-1>", self._toggle_clicked)
        self.listbox.bind("<space>", self._toggle_focused)
        self.listbox.bind("<MouseWheel>", self._on_mousewheel)
        self.listbox.bind("<Button-4>", self._on_mousewheel)
        self.listbox.bind("<Button-5>", self._on_mousewheel)
        self.listbox.bind("<Enter>", self._bind_mousewheel)
        self.listbox.bind("<Leave>", self._unbind_mousewheel)

    def set_items(self, names: list[str], selected: list[str] | None = None) -> None:
        self.names = list(names)
        selected_set = set(names if selected is None else selected)
        self.selected = {name for name in self.names if name in selected_set}
        self._refresh()

    def _refresh(self, keep_scroll: bool = False, active_index: int | None = None) -> None:
        yview = self.listbox.yview()[0] if keep_scroll else 0
        self.listbox.delete(0, END)
        for name in self.names:
            mark = "☑" if name in self.selected else "☐"
            self.listbox.insert(END, f"{mark} {name}")
        if keep_scroll:
            self.listbox.yview_moveto(yview)
        if active_index is not None and 0 <= active_index < len(self.names):
            self.listbox.selection_set(active_index)
            self.listbox.activate(active_index)

    def selected_items(self) -> list[str]:
        return [name for name in self.names if name in self.selected]

    def select_all(self, checked: bool) -> None:
        self.selected = set(self.names) if checked else set()
        self._refresh()

    def _toggle_clicked(self, _event) -> None:
        if not self.listbox.curselection():
            return
        self._toggle_index(self.listbox.curselection()[0])

    def _toggle_focused(self, _event) -> str:
        if self.listbox.curselection():
            self._toggle_index(self.listbox.curselection()[0])
        return "break"

    def _toggle_index(self, index: int) -> None:
        if index < 0 or index >= len(self.names):
            return
        name = self.names[index]
        if name in self.selected:
            self.selected.remove(name)
        else:
            self.selected.add(name)
        self._refresh(keep_scroll=True, active_index=index)
        self._notify_change()

    def _on_mousewheel(self, event) -> str:
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 if event.delta > 0 else 1 if event.delta < 0 else 0
        self.listbox.yview_scroll(delta, "units")
        return "break"

    def _bind_mousewheel(self, _event) -> None:
        self.listbox.bind_all("<MouseWheel>", self._on_mousewheel)
        self.listbox.bind_all("<Button-4>", self._on_mousewheel)
        self.listbox.bind_all("<Button-5>", self._on_mousewheel)

    def _unbind_mousewheel(self, _event) -> None:
        self.listbox.unbind_all("<MouseWheel>")
        self.listbox.unbind_all("<Button-4>")
        self.listbox.unbind_all("<Button-5>")

    def _notify_change(self) -> None:
        if self.on_change:
            self.on_change()


class GovReportApp(Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("政府政策周报生成工具")
        self.geometry("1080x820")
        self.minsize(960, 700)

        today = dt.date.today()
        default_end = today - dt.timedelta(days=1)
        default_start = default_end - dt.timedelta(days=6)
        settings = self._load_settings()

        self.start_date = StringVar(value=settings.get("start_date", default_start.strftime("%Y-%m-%d")))
        self.end_date = StringVar(value=settings.get("end_date", default_end.strftime("%Y-%m-%d")))
        self.output_root = StringVar(value=settings.get("output_root", str(DEFAULT_OUTPUT_ROOT)))
        self.sleep_seconds = StringVar(value=settings.get("sleep_seconds", "0.5"))
        self.openai_base_url = StringVar(value=settings.get("openai_base_url", ""))
        self.openai_api_key = StringVar(value=settings.get("openai_api_key", ""))
        self.openai_model = StringVar(value=settings.get("openai_model", "gpt-5.4"))
        self.model_options = settings.get("model_options", [])

        self.select_all_sources = BooleanVar(value=settings.get("select_all_sources", True))
        self.use_llm = BooleanVar(value=settings.get("use_llm", True))
        self.download_attachments = BooleanVar(value=settings.get("download_attachments", True))
        self.browser_fallback = BooleanVar(value=settings.get("browser_fallback", True))
        self.strict_mode = BooleanVar(value=settings.get("strict_mode", True))
        self.verify_ssl = BooleanVar(value=settings.get("verify_ssl", True))
        self.allow_rule_fallback = BooleanVar(value=settings.get("allow_rule_fallback", False))

        self.source_data: list[dict] = []
        self.source_names: list[str] = []
        self.selected_source_names: set[str] = set()
        self.saved_selected_sources = settings.get("selected_sources", [])
        self.source_summary = StringVar(value="正在加载站点")
        self.source_dropdown_open = False
        self.source_close_binding: str | None = None
        self.active_date_picker: DatePicker | None = None
        self.process: subprocess.Popen[str] | None = None
        self.log_queue: queue.Queue[object] = queue.Queue()
        self.last_output_dir: Path | None = None

        self._build_ui()
        self._load_sources()
        self._append_dependency_notes()
        self.after(100, self._drain_log_queue)

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        top = ttk.Frame(self, padding=16)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)
        top.columnconfigure(3, weight=1)

        ttk.Label(top, text="开始日期").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=6)
        self.start_date_field = self._dropdown_field(top, self.start_date, width=16)
        self.start_date_field.grid(row=0, column=1, sticky="w", pady=6)
        self._bind_dropdown_field(self.start_date_field, lambda: self._toggle_date_picker(self.start_date, self.start_date_field))
        ttk.Label(top, text="结束日期").grid(row=0, column=2, sticky="w", padx=(24, 8), pady=6)
        self.end_date_field = self._dropdown_field(top, self.end_date, width=16)
        self.end_date_field.grid(row=0, column=3, sticky="w", pady=6)
        self._bind_dropdown_field(self.end_date_field, lambda: self._toggle_date_picker(self.end_date, self.end_date_field))

        quick = ttk.Frame(top)
        quick.grid(row=0, column=4, sticky="e", padx=(20, 0), pady=6)
        ttk.Button(quick, text="最近7天", command=lambda: self._set_recent_days(7)).pack(side="left", padx=3)
        ttk.Button(quick, text="最近30天", command=lambda: self._set_recent_days(30)).pack(side="left", padx=3)

        ttk.Label(top, text="输出目录").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=6)
        ttk.Entry(top, textvariable=self.output_root).grid(row=1, column=1, columnspan=3, sticky="ew", pady=6)
        ttk.Button(top, text="选择", command=self._choose_output_root).grid(row=1, column=4, sticky="w", padx=(12, 0), pady=6)

        llm_frame = ttk.LabelFrame(top, text="大模型配置", padding=12)
        llm_frame.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(12, 0))
        llm_frame.columnconfigure(1, weight=1)
        llm_frame.columnconfigure(3, weight=1)
        ttk.Checkbutton(llm_frame, text="启用 GPT 复判", variable=self.use_llm).grid(row=0, column=0, sticky="w", pady=4)
        ttk.Label(llm_frame, text="API URL").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(llm_frame, textvariable=self.openai_base_url).grid(row=1, column=1, columnspan=3, sticky="ew", pady=4)
        ttk.Label(llm_frame, text="API Key").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(llm_frame, textvariable=self.openai_api_key, show="●").grid(row=2, column=1, columnspan=3, sticky="ew", pady=4)
        self.fetch_models_button = ttk.Button(llm_frame, text="获取模型", command=self._fetch_models)
        self.fetch_models_button.grid(row=2, column=4, sticky="w", padx=(12, 0), pady=4)
        ttk.Label(llm_frame, text="模型").grid(row=3, column=0, sticky="w", pady=4)
        self.model_box = ttk.Combobox(
            llm_frame,
            textvariable=self.openai_model,
            values=self.model_options,
            width=28,
            state="readonly",
        )
        self.model_box.grid(row=3, column=1, sticky="w", pady=4)

        settings = ttk.LabelFrame(top, text="运行设置", padding=12)
        settings.grid(row=3, column=0, columnspan=5, sticky="ew", pady=(12, 0))
        for i in range(8):
            settings.columnconfigure(i, weight=1)

        ttk.Checkbutton(settings, text="下载附件", variable=self.download_attachments).grid(row=0, column=0, sticky="w", pady=4)
        ttk.Checkbutton(settings, text="浏览器兜底", variable=self.browser_fallback).grid(row=0, column=1, sticky="w", pady=4)
        ttk.Checkbutton(settings, text="严格模式", variable=self.strict_mode).grid(row=0, column=2, sticky="w", pady=4)
        ttk.Checkbutton(settings, text="校验 SSL", variable=self.verify_ssl).grid(row=0, column=3, sticky="w", pady=4)
        ttk.Checkbutton(settings, text="规则兜底", variable=self.allow_rule_fallback).grid(row=0, column=4, sticky="w", pady=4)
        ttk.Label(settings, text="请求间隔秒").grid(row=1, column=0, sticky="w", pady=(10, 4))
        ttk.Entry(settings, textvariable=self.sleep_seconds, width=8).grid(row=1, column=1, sticky="w", pady=(10, 4))

        source_frame = ttk.LabelFrame(top, text="采集站点", padding=12)
        source_frame.grid(row=4, column=0, columnspan=5, sticky="ew", pady=(12, 0))
        source_frame.columnconfigure(1, weight=1)
        ttk.Label(source_frame, text="站点范围").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.source_field = self._dropdown_field(source_frame, self.source_summary, width=48)
        self.source_field.grid(row=0, column=1, sticky="ew")
        self._bind_dropdown_field(self.source_field, self._toggle_source_popup)

        self.source_dropdown = ttk.Frame(source_frame, padding=(0, 8, 0, 0))
        self.source_dropdown.grid(row=1, column=1, sticky="ew")
        self.source_dropdown.columnconfigure(0, weight=1)
        ttk.Checkbutton(
            self.source_dropdown,
            text="全部站点",
            variable=self.select_all_sources,
            command=self._toggle_all_sources,
        ).grid(row=0, column=0, sticky="w", pady=(0, 6))
        self.popup_source_checks = ScrollableChecks(self.source_dropdown, on_change=self._sync_select_all_state)
        self.popup_source_checks.grid(row=1, column=0, sticky="ew")
        self.source_dropdown.grid_remove()

        actions = ttk.Frame(top)
        actions.grid(row=5, column=0, columnspan=5, sticky="ew", pady=(14, 0))
        actions.columnconfigure(5, weight=1)

        self.run_button = ttk.Button(actions, text="开始生成", command=self._start_run)
        self.run_button.grid(row=0, column=0, padx=(0, 8))
        self.stop_button = ttk.Button(actions, text="停止", command=self._stop_run, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=8)
        ttk.Button(actions, text="打开输出目录", command=self._open_output_root).grid(row=0, column=2, padx=8)
        ttk.Button(actions, text="打开本次结果", command=self._open_last_output).grid(row=0, column=3, padx=8)
        ttk.Button(actions, text="清空日志", command=self._clear_log).grid(row=0, column=4, padx=8)

        log_frame = ttk.Frame(self, padding=(16, 0, 16, 16))
        log_frame.grid(row=1, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log_text = Text(log_frame, wrap="word", height=16)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.status = StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status, anchor="w", padding=(16, 0, 16, 10)).grid(row=2, column=0, sticky="ew")

    def _dropdown_field(self, parent, variable: StringVar, width: int) -> tk.Frame:
        frame = tk.Frame(parent, background="#bcbcbc", borderwidth=1, relief="solid")
        frame.columnconfigure(0, weight=1)
        entry = tk.Entry(
            frame,
            textvariable=variable,
            width=width,
            borderwidth=0,
            relief="flat",
            readonlybackground="white",
            background="white",
            foreground="#111111",
            highlightthickness=0,
            font=("", 13),
        )
        entry.configure(state="readonly")
        entry.grid(row=0, column=0, sticky="ew", ipady=3, padx=(6, 0))
        arrow = tk.Button(
            frame,
            text="▾",
            width=2,
            padx=0,
            pady=0,
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
            background="white",
            activebackground="white",
            foreground="#111111",
            activeforeground="#111111",
            cursor="hand2",
            font=("", 11),
        )
        arrow.grid(row=0, column=1, sticky="ns", padx=(0, 4))
        frame.dropdown_entry = entry  # type: ignore[attr-defined]
        frame.dropdown_arrow = arrow  # type: ignore[attr-defined]
        return frame

    def _bind_dropdown_field(self, field: tk.Frame, command) -> None:
        def run(_event=None):
            command()
            return "break"

        field.configure(cursor="hand2")
        field.dropdown_arrow.configure(command=command)  # type: ignore[attr-defined]
        field.bind("<Button-1>", run)
        field.dropdown_entry.bind("<Button-1>", run)  # type: ignore[attr-defined]

    def _load_sources(self) -> None:
        config_path = RESOURCE_DIR / "config" / "sources.yaml"
        self.source_data = []
        if yaml and config_path.exists():
            try:
                data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or []
                if isinstance(data, list):
                    self.source_data = [item for item in data if isinstance(item, dict) and item.get("name")]
            except Exception as exc:  # pragma: no cover - UI fallback.
                self._append_log(f"读取站点配置失败：{exc}\n")
        if not self.source_data and config_path.exists():
            names = self._fallback_source_names(config_path)
            self.source_data = [{"name": name, "base_url": "", "list_urls": []} for name in names]
        self.source_names = [str(item["name"]) for item in self.source_data]
        if self.select_all_sources.get():
            self.selected_source_names = set(self.source_names)
        else:
            self.selected_source_names = {name for name in self.saved_selected_sources if name in self.source_names}
        if not self.selected_source_names and self.source_names:
            self.selected_source_names = set(self.source_names)
            self.select_all_sources.set(True)
        self._refresh_source_summary()
        self.popup_source_checks.set_items(self.source_names, selected=self._selected_sources())
        self._append_log(f"已加载采集站点：{len(self.source_names)} 个\n")

    def _toggle_all_sources(self) -> None:
        if hasattr(self, "popup_source_checks") and self.popup_source_checks.winfo_exists():
            self.popup_source_checks.select_all(self.select_all_sources.get())
        self.selected_source_names = set(self.source_names) if self.select_all_sources.get() else set()
        self._refresh_source_summary()

    def _sync_select_all_state(self) -> None:
        selected = set(self.popup_source_checks.selected_items())
        self.selected_source_names = selected
        all_names = set(self.source_names)
        self.select_all_sources.set(bool(all_names) and selected == all_names)
        self._refresh_source_summary()

    def _toggle_date_picker(self, target_var: StringVar, anchor_widget) -> None:
        if self.active_date_picker and self.active_date_picker.winfo_exists():
            self.active_date_picker.destroy()
            return
        self.active_date_picker = DatePicker(self, target_var, anchor_widget, on_close=self._date_picker_closed)

    def _date_picker_closed(self, picker: DatePicker) -> None:
        if self.active_date_picker is picker:
            self.active_date_picker = None

    def _toggle_source_popup(self) -> None:
        if self.source_dropdown_open:
            self._close_source_dropdown()
        else:
            self._open_source_dropdown()

    def _open_source_dropdown(self) -> None:
        self.popup_source_checks.set_items(self.source_names, selected=self._selected_sources())
        self.source_dropdown.grid()
        self.source_dropdown_open = True
        self.after(120, self._bind_source_dropdown_close)

    def _close_source_dropdown(self) -> None:
        self.source_dropdown.grid_remove()
        self.source_dropdown_open = False
        if self.source_close_binding:
            try:
                self.unbind_all("<Button-1>")
            except Exception:
                pass
            self.source_close_binding = None

    def _bind_source_dropdown_close(self) -> None:
        if self.source_close_binding:
            return
        self.source_close_binding = self.bind_all("<Button-1>", self._close_source_dropdown_from_click, add="+")

    def _close_source_dropdown_from_click(self, _event) -> None:
        pointer_x = self.winfo_pointerx()
        pointer_y = self.winfo_pointery()
        if self._point_inside_widget(self.source_field, pointer_x, pointer_y):
            return
        if self._point_inside_widget(self.source_dropdown, pointer_x, pointer_y):
            return
        self._close_source_dropdown()

    @staticmethod
    def _point_inside_widget(widget, pointer_x: int, pointer_y: int) -> bool:
        if not widget.winfo_ismapped():
            return False
        x = widget.winfo_rootx()
        y = widget.winfo_rooty()
        return x <= pointer_x <= x + widget.winfo_width() and y <= pointer_y <= y + widget.winfo_height()

    def _selected_sources(self) -> list[str]:
        return [name for name in self.source_names if name in self.selected_source_names]

    def _refresh_source_summary(self) -> None:
        count = len(self.selected_source_names)
        total = len(self.source_names)
        if total and count == total:
            self.source_summary.set(f"全部站点（{total} 个）")
        elif count == 0:
            self.source_summary.set("未选择站点")
        elif count <= 3:
            self.source_summary.set("、".join(self._selected_sources()))
        else:
            self.source_summary.set(f"已选择 {count} 个站点")

    def _fetch_models(self) -> None:
        base_url = self.openai_base_url.get().strip()
        api_key = self.openai_api_key.get().strip()
        if not base_url:
            messagebox.showerror("参数错误", "请先填写 API URL")
            return
        if not api_key:
            messagebox.showerror("参数错误", "请先填写 API Key")
            return
        self.fetch_models_button.configure(state="disabled")
        self.status.set("正在获取模型列表")
        self._append_log(">>> 正在获取模型列表...\n")
        self._save_settings(self._selected_sources())
        threading.Thread(target=self._fetch_models_worker, args=(base_url, api_key), daemon=True).start()

    def _fetch_models_worker(self, base_url: str, api_key: str) -> None:
        errors = []
        try:
            headers = {"Authorization": f"Bearer {api_key}"}
            for url in self._candidate_model_urls(base_url):
                try:
                    resp = requests.get(url, headers=headers, timeout=30)
                    if resp.status_code >= 400:
                        errors.append(f"{url} -> HTTP {resp.status_code}: {resp.text[:300]}")
                        continue
                    data = resp.json()
                    models = self._parse_model_response(data)
                    if models:
                        self.log_queue.put({"type": "models", "models": models, "url": url})
                        return
                    errors.append(f"{url} -> 已连接，但返回中没有找到模型 id")
                except Exception as exc:
                    errors.append(f"{url} -> {exc}")
            raise RuntimeError("；".join(errors))
        except Exception as exc:
            self.log_queue.put({"type": "model_error", "error": str(exc)})

    @staticmethod
    def _candidate_model_urls(base_url: str) -> list[str]:
        normalized = base_url.strip().rstrip("/")
        lower = normalized.lower()
        for suffix in ["/chat/completions", "/responses", "/models"]:
            if lower.endswith(suffix):
                normalized = normalized[: -len(suffix)]
                lower = normalized.lower()
                break
        urls = [urljoin(normalized.rstrip("/") + "/", "models")]
        if not lower.endswith("/v1"):
            urls.append(urljoin(normalized.rstrip("/") + "/", "v1/models"))
        seen = []
        for url in urls:
            if url not in seen:
                seen.append(url)
        return seen

    @staticmethod
    def _parse_model_response(data) -> list[str]:
        models = []
        if isinstance(data, dict) and isinstance(data.get("data"), list):
            items = data["data"]
        elif isinstance(data, list):
            items = data
        else:
            items = []
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
            elif isinstance(item, str):
                models.append(item)
        return sorted(set(models))

    def _set_recent_days(self, days: int) -> None:
        today = dt.date.today()
        end = today - dt.timedelta(days=1)
        start = end - dt.timedelta(days=days - 1)
        self.start_date.set(start.strftime("%Y-%m-%d"))
        self.end_date.set(end.strftime("%Y-%m-%d"))

    def _choose_output_root(self) -> None:
        selected = filedialog.askdirectory(initialdir=self.output_root.get() or str(APP_DIR))
        if selected:
            self.output_root.set(selected)

    def _start_run(self) -> None:
        if self.process and self.process.poll() is None:
            messagebox.showinfo("正在运行", "当前任务还没有结束。")
            return

        try:
            start = self._parse_date(self.start_date.get(), "开始日期")
            end = self._parse_date(self.end_date.get(), "结束日期")
            if start > end:
                raise ValueError("开始日期不能晚于结束日期")
            sleep_seconds = self._parse_non_negative_float(self.sleep_seconds.get(), "请求间隔秒")
        except ValueError as exc:
            messagebox.showerror("参数错误", str(exc))
            return

        selected_sources = self._selected_sources()
        all_names = [str(item["name"]) for item in self.source_data]
        if not selected_sources:
            messagebox.showerror("参数错误", "请至少选择一个采集站点")
            return
        use_all_sources = set(selected_sources) == set(all_names)
        self.select_all_sources.set(use_all_sources)

        output_root = Path(self.output_root.get()).expanduser()
        self.last_output_dir = output_root / f"{start:%Y-%m-%d}_至_{end:%Y-%m-%d}"
        sources_path = self._write_runtime_sources(selected_sources, use_all_sources)
        self._save_settings(selected_sources)

        cmd = [sys.executable]
        if getattr(sys, "frozen", False):
            cmd.append("--run-cli")
        else:
            cmd.extend(["-u", str(APP_DIR / "main.py")])
        cmd.extend([
            "--start-date",
            start.strftime("%Y-%m-%d"),
            "--end-date",
            end.strftime("%Y-%m-%d"),
            "--output-root",
            str(output_root),
            "--sources",
            str(sources_path),
            "--keywords",
            str(RESOURCE_DIR / "config" / "keywords.yaml"),
            "--manual-urls",
            str(RESOURCE_DIR / "input" / "manual_urls.txt"),
            "--max-channels-per-source",
            NO_LIMIT_VALUE,
            "--max-detail-per-source",
            NO_LIMIT_VALUE,
            "--sleep",
            str(sleep_seconds),
        ])

        if not self.use_llm.get():
            cmd.append("--no-llm")
        if not self.download_attachments.get():
            cmd.append("--no-download-attachments")
        if not self.browser_fallback.get():
            cmd.append("--no-browser-fallback")
        if not self.strict_mode.get():
            cmd.append("--loose")
        if not self.verify_ssl.get():
            cmd.append("--no-verify-ssl")
        if self.allow_rule_fallback.get():
            cmd.append("--allow-rule-fallback")

        self._append_log("\n>>> 启动任务\n")
        self._append_log("栏目和详情已按无上限模式运行；实际耗时取决于站点链接数量。\n")
        self._append_log(" ".join(f'"{part}"' if " " in part else part for part in cmd) + "\n\n")

        env = os.environ.copy()
        env["PYTHONUTF8"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"
        if self.openai_api_key.get().strip():
            env["GOV_REPORT_OPENAI_API_KEY"] = self.openai_api_key.get().strip()
        if self.openai_base_url.get().strip():
            env["GOV_REPORT_OPENAI_BASE_URL"] = self.openai_base_url.get().strip()
        if self.openai_model.get().strip():
            env["GOV_REPORT_OPENAI_MODEL"] = self.openai_model.get().strip()

        if self.browser_fallback.get() and not self._playwright_available():
            self._append_log("提示：当前 Python 环境未检测到 Playwright。浏览器兜底可能无法生效。\n")
        if not self._libreoffice_available():
            self._append_log("提示：未检测到 LibreOffice，将使用内置 PDF 引擎直接生成 PDF。\n")

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(APP_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=False,
                env=env,
            )
        except Exception as exc:
            messagebox.showerror("启动失败", str(exc))
            self.process = None
            return

        self.status.set("运行中")
        self.run_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _write_runtime_sources(self, selected_sources: list[str], use_all_sources: bool) -> Path:
        RUNTIME_DIR.mkdir(exist_ok=True)
        path = RUNTIME_DIR / "selected_sources.yaml"
        if use_all_sources:
            selected_data = self.source_data
        else:
            selected_set = set(selected_sources)
            selected_data = [item for item in self.source_data if str(item.get("name")) in selected_set]
        if yaml:
            text = yaml.safe_dump(selected_data, allow_unicode=True, sort_keys=False)
        else:
            text = json.dumps(selected_data, ensure_ascii=False, indent=2)
        path.write_text(text, encoding="utf-8")
        return path

    def _read_process_output(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.log_queue.put(self._decode_process_line(line))
        code = self.process.wait()
        self.log_queue.put(f"\n>>> 任务结束，退出码：{code}\n")
        self.log_queue.put("__PROCESS_DONE__")

    @staticmethod
    def _decode_process_line(line: bytes) -> str:
        candidates = []
        for encoding in ("utf-8", "gb18030", "cp936"):
            try:
                text = line.decode(encoding)
            except UnicodeDecodeError:
                text = line.decode(encoding, errors="replace")
            candidates.append(text)
        return max(candidates, key=GovReportApp._chinese_text_score)

    @staticmethod
    def _chinese_text_score(text: str) -> int:
        cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
        bad = text.count("�") * 5
        mojibake = sum(text.count(ch) for ch in "ÃÂÐÑÍÎÏ¼½¾")
        return cjk * 3 - bad - mojibake

    def _drain_log_queue(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            if line == "__PROCESS_DONE__":
                self.process = None
                self.run_button.configure(state="normal")
                self.stop_button.configure(state="disabled")
                self.status.set("已完成")
            elif isinstance(line, dict) and line.get("type") == "models":
                models = line["models"]
                self.model_options = models
                self.model_box.configure(values=models, state="readonly")
                if self.openai_model.get() not in models:
                    self.openai_model.set(models[0])
                self.fetch_models_button.configure(state="normal")
                self.status.set("模型列表已更新")
                self._append_log(f">>> 已从 {line.get('url')} 获取 {len(models)} 个模型\n")
                self._save_settings(self._selected_sources())
            elif isinstance(line, dict) and line.get("type") == "model_error":
                self.fetch_models_button.configure(state="normal")
                self.status.set("获取模型失败")
                self._append_log(f">>> 获取模型失败：{line.get('error')}\n")
            else:
                self._append_log(line)
        self.after(100, self._drain_log_queue)

    def _stop_run(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.status.set("正在停止")
            self._append_log("\n>>> 已请求停止任务\n")

    def _append_log(self, text: str) -> None:
        at_bottom = self.log_text.yview()[1] >= 0.999
        self.log_text.insert(END, text)
        if at_bottom:
            self.log_text.see(END)

    def _append_dependency_notes(self) -> None:
        if not self._libreoffice_available():
            self._append_log("环境提示：未检测到 LibreOffice；PDF 会使用内置引擎生成。\n")
        if not self._playwright_available():
            self._append_log("环境提示：未检测到 Playwright，浏览器兜底需安装后才能使用。\n")

    def _clear_log(self) -> None:
        self.log_text.delete("1.0", END)

    def _open_output_root(self) -> None:
        self._open_path(Path(self.output_root.get()).expanduser())

    def _open_last_output(self) -> None:
        if not self.last_output_dir:
            messagebox.showinfo("暂无结果", "还没有启动过任务。")
            return
        self._open_path(self.last_output_dir)

    def _open_path(self, path: Path) -> None:
        if not path.exists():
            messagebox.showinfo("路径不存在", str(path))
            return
        if sys.platform.startswith("win"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def _load_settings(self) -> dict:
        if not SETTINGS_PATH.exists():
            return {}
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_settings(self, selected_sources: list[str]) -> None:
        data = {
            "start_date": self.start_date.get(),
            "end_date": self.end_date.get(),
            "output_root": self.output_root.get(),
            "sleep_seconds": self.sleep_seconds.get(),
            "openai_base_url": self.openai_base_url.get(),
            "openai_api_key": self.openai_api_key.get(),
            "openai_model": self.openai_model.get(),
            "model_options": self.model_options,
            "select_all_sources": self.select_all_sources.get(),
            "selected_sources": selected_sources,
            "use_llm": self.use_llm.get(),
            "download_attachments": self.download_attachments.get(),
            "browser_fallback": self.browser_fallback.get(),
            "strict_mode": self.strict_mode.get(),
            "verify_ssl": self.verify_ssl.get(),
            "allow_rule_fallback": self.allow_rule_fallback.get(),
        }
        SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _fallback_source_names(path: Path) -> list[str]:
        names = []
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("- name:") or stripped.startswith("name:"):
                name = stripped.split(":", 1)[1].strip().strip("'\"")
                if name:
                    names.append(name)
        return names

    @staticmethod
    def _playwright_available() -> bool:
        try:
            import playwright  # noqa: F401
        except Exception:
            return False
        return True

    @staticmethod
    def _libreoffice_available() -> bool:
        candidates = ["soffice", "libreoffice"]
        app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else APP_DIR
        candidates.extend(
            [
                app_dir / "LibreOffice" / "program" / "soffice.exe",
                app_dir / "_internal" / "LibreOffice" / "program" / "soffice.exe",
            ]
        )
        if sys.platform.startswith("win"):
            candidates.extend(
                [
                    r"C:\Program Files\LibreOffice\program\soffice.exe",
                    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
                ]
            )
        return any(shutil.which(candidate) or Path(candidate).exists() for candidate in candidates)

    @staticmethod
    def _parse_date(value: str, label: str) -> dt.date:
        try:
            return dt.datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(f"{label}格式应为 YYYY-MM-DD") from exc

    @staticmethod
    def _parse_non_negative_float(value: str, label: str) -> float:
        try:
            parsed = float(value.strip())
        except ValueError as exc:
            raise ValueError(f"{label}必须是数字") from exc
        if parsed < 0:
            raise ValueError(f"{label}不能小于 0")
        return parsed


def run_cli_from_frozen() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    from main import main

    main()


if __name__ == "__main__":
    if "--run-cli" in sys.argv:
        sys.argv.remove("--run-cli")
        run_cli_from_frozen()
    else:
        GovReportApp().mainloop()
