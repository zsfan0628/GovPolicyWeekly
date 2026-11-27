"""Independent, offline design preview. Does not start the collection engine."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from gov_report.config import load_sources
from gov_report.scope import core_urls
from gov_report.ui_fonts import configure_workspace_fonts
from PySide6.QtCore import (
    QAbstractListModel, QMetaObject, QModelIndex, QObject, Property, QSortFilterProxyModel,
    Qt, QTimer, QUrl, Signal, Slot,
)
from PySide6.QtGui import QColor, QDesktopServices, QImage, QPainter
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickImageProvider, QQuickWindow
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QApplication, QFileDialog


ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
APP_DIR = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else ROOT
UI = ROOT / "ui" / "preview"


class Rows(QAbstractListModel):
    def __init__(self, rows, fields):
        super().__init__()
        self.rows = rows
        self.roles = {Qt.UserRole + i + 1: name for i, name in enumerate(fields)}

    def roleNames(self):
        return {key: value.encode() for key, value in self.roles.items()}

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.rows)

    def data(self, index, role):
        if index.isValid() and 0 <= index.row() < len(self.rows):
            return self.rows[index.row()].get(self.roles.get(role))
        return None

    def append(self, row):
        position = len(self.rows)
        self.beginInsertRows(QModelIndex(), position, position)
        self.rows.append(row)
        self.endInsertRows()

    def replace(self, rows):
        self.beginResetModel()
        self.rows = list(rows)
        self.endResetModel()

    def clear(self):
        self.beginResetModel()
        self.rows.clear()
        self.endResetModel()


class TaskActivity(Rows):
    """A bounded-by-task timeline: update a milestone in place, don't mirror stdout."""
    def __init__(self):
        super().__init__([], ["eventTime", "eventKind", "eventTitle", "eventDetail", "eventAction"])
        self.index_by_key = {}

    def put(self, key, kind, title, detail="", action=""):
        fields = dict(eventKind=kind, eventTitle=title, eventDetail=detail, eventAction=action)
        i = self.index_by_key.get(key)
        if i is not None and all(self.rows[i][k] == v for k, v in fields.items()):
            return
        fields["eventTime"] = datetime.now().strftime("%H:%M")
        if i is None:
            self.index_by_key[key] = len(self.rows)
            self.append(fields)
        else:
            self.rows[i].update(fields)
            self.dataChanged.emit(self.index(i), self.index(i), list(self.roles))

    def clear(self):
        self.index_by_key.clear()
        super().clear()

    def interrupt(self, detail):
        for key, i in self.index_by_key.items():
            row = self.rows[i]
            if row["eventKind"] == "working":
                self.put(key, "paused", row["eventTitle"], detail)


class Sources(Rows):
    selectionChanged = Signal()
    catalogueChanged = Signal()

    def __init__(self, path=None):
        sources = load_sources(path or ROOT / "config" / "sources.yaml")
        self.source_data = sources
        from gov_report.config import load_yaml
        self.locations = load_yaml(ROOT/'config'/'map-regions.yaml')
        super().__init__(self._rows(sources), ["siteId", "siteName", "region", "department", "siteUrl", "channels", "selected"])

    @staticmethod
    def _rows(sources):
        regions = ["国家", "江苏", "湖北", "黑龙江", "南通"]
        sources = sorted(sources, key=lambda row: regions.index(row["region"]) if row.get("region") in regions else len(regions))
        rows = [dict(
            siteId=i, siteName=row["name"], region=row.get("region", ""),
            department=row.get("department", ""), siteUrl=row["base_url"],
            channels=len(core_urls(row)), selected=True,
        ) for i, row in enumerate(sources)]
        return rows

    def install(self, data, locations):
        selected = {r['siteName'] for r in self.rows if r['selected']}
        rows = self._rows(data)
        for row in rows:
            row['selected'] = row['siteName'] in selected
        self.source_data, self.locations = data, locations
        self.replace(rows)
        self.catalogueChanged.emit()
        self.selectionChanged.emit()

    @Property('QVariantList', notify=catalogueChanged)
    def mapLocations(self):
        regions = {s['region'] for s in self.rows}
        return [loc for loc in self.locations if loc['region'] in regions]

    @Property(int, notify=selectionChanged)
    def departments(self):
        return len({s['department'] for s in self.rows})

    @Property(int, notify=selectionChanged)
    def selectedCount(self):
        return sum(row["selected"] for row in self.rows)

    @Property(int, notify=selectionChanged)
    def total(self):
        return len(self.rows)

    @Property('QVariantMap', notify=selectionChanged)
    def regionCounts(self):
        result = {}
        for row in self.rows:
            entry = result.setdefault(row['region'], {'total': 0, 'selected': 0})
            entry['total'] += 1
            entry['selected'] += int(row['selected'])
        return result

    @Slot(str, bool)
    def selectRegion(self, region, selected):
        for row in self.rows:
            if row['region'] == region and row['selected'] != selected:
                self.toggle(row['siteId'])

    @Slot(int)
    def toggle(self, site_id):
        if not 0 <= site_id < len(self.rows):
            return
        self.rows[site_id]["selected"] = not self.rows[site_id]["selected"]
        role = next(role for role, name in self.roles.items() if name == "selected")
        self.dataChanged.emit(self.index(site_id), self.index(site_id), [role])
        self.selectionChanged.emit()

    @Slot(bool)
    def selectAll(self, selected):
        for row in self.rows:
            row["selected"] = selected
        if self.rows:
            role = next(role for role, name in self.roles.items() if name == "selected")
            self.dataChanged.emit(self.index(0), self.index(len(self.rows) - 1), [role])
        self.selectionChanged.emit()


class SourceFilter(QSortFilterProxyModel):
    queryChanged = Signal()

    def __init__(self, model, fields=("siteName", "region", "department", "siteUrl"), dynamic=False):
        super().__init__()
        self._query = ""
        self._region = ""
        self._fields = fields
        self.setSourceModel(model)
        # Selection edits must not rebuild or reorder the filtered list.
        self.setDynamicSortFilter(dynamic)

    @Property(str, notify=queryChanged)
    def query(self):
        return self._query

    @query.setter
    def query(self, value):
        if value != self._query:
            self._query = value
            self.beginFilterChange()
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
            self.queryChanged.emit()

    def filterAcceptsRow(self, row, parent):
        source = self.sourceModel().rows[row]
        if self._region and source.get('region') != self._region:
            return False
        return self._query.strip().lower() in " ".join(
            str(source[key]) for key in self._fields
        ).lower()

    @Property(str, notify=queryChanged)
    def region(self):
        return self._region

    @region.setter
    def region(self, value):
        if value != self._region:
            self._region = value
            self.beginFilterChange()
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
            self.queryChanged.emit()


class Icons(QQuickImageProvider):
    def __init__(self):
        super().__init__(QQuickImageProvider.Image)

    def requestImage(self, image_id, size, requested_size):
        name, _, color = image_id.partition("/")
        path = UI / "icons" / (Path(name).name + ".svg")
        dimension = requested_size.width() if requested_size.width() > 0 else 48
        image = QImage(dimension, dimension, QImage.Format_ARGB32_Premultiplied)
        image.fill(Qt.transparent)
        if path.exists():
            renderer = QSvgRenderer(str(path))
            painter = QPainter(image)
            renderer.render(painter)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(image.rect(), QColor("#" + (color or "96999f")))
            painter.end()
        return image


class Workspace(QObject):
    latestReportChanged = Signal()
    changed = Signal()
    toast = Signal(str)
    logAdded = Signal()
    modelsChanged = Signal()
    settingsChanged = Signal()
    closeReady = Signal()
    apiBaseResolved = Signal(str)

    def __init__(self, sources):
        super().__init__()
        self.sources = sources
        self.logs = Rows([], ["logTime", "level", "message"])
        self.activity = TaskActivity()
        self.reports = Rows([], ["reportName", "reportPath", "reportDate", "reportSize"])
        self.reports.modelReset.connect(self.latestReportChanged.emit)
        self._model_options = []
        self._initial_settings = {}
        self._elapsed_seconds = 0
        self._running = False
        self._step = 0
        self._done = 0
        self._pages = 0
        self._hits = 0
        self._state = "待开始"
        self._current = "等待开始"
        self._phase = "准备就绪"
        self._output = str(APP_DIR / "output")
        self._active = []
        self._stage_stats = {}
        self._active_sources = {}
        self._current_column = ""

    @Property(bool, constant=True)
    def isDemo(self):
        return False

    @Property(QObject, constant=True)
    def activityModel(self):
        return self.activity

    @Property(QObject, constant=True)
    def updater(self):
        return getattr(self, '_updater', None)

    @Property(str, constant=True)
    def buildLabel(self):
        try:
            return (ROOT / "config" / "build-id.txt").read_text(encoding="utf-8-sig").strip()
        except OSError:
            return "本地源码"

    @Property("QVariantMap", constant=True)
    def initialSettings(self):
        return self._initial_settings

    @Property("QStringList", notify=modelsChanged)
    def modelOptions(self):
        return self._model_options

    @Property(bool, notify=modelsChanged)
    def modelsLoading(self):
        return getattr(self, "_models_loading", False)

    @Property(bool, notify=changed)
    def modelTesting(self):
        return getattr(self, "_model_testing", False)

    @Property(str, notify=changed)
    def modelTestResult(self):
        return getattr(self, "_model_test_result", "")

    @Property(bool, notify=changed)
    def hasTask(self):
        return bool(getattr(self, "_task_path", ""))

    @Property("QVariantList", notify=changed)
    def coverageSources(self):
        return getattr(self, "_coverage", {}).get("sources", [])

    @Property(str, notify=changed)
    def coverageText(self):
        data = getattr(self, "_coverage", {})
        if not data:
            return "尚无任务覆盖记录"
        counts = data.get("counts", {})
        return (f"{data.get('start_date', '')} 至 {data.get('end_date', '')}\n"
                f"站点：{data.get('complete', 0)} 完成 · {data.get('partial', 0)} 部分失败 · "
                f"{data.get('failed', 0)} 采集失败 · {data.get('pending', 0)} 未完成\n"
                f"候选：{counts.get('included', 0)} 收录 · {counts.get('excluded', 0)} 排除 · "
                f"{counts.get('llm_failed', 0)} 待复判 · {counts.get('detail_failed', 0)} 详情异常或待核查 · "
                f"{counts.get('historical_hint', 0)} 仅见期前日期线索\n"
                f"非正文附件正常跳过 {counts.get('skipped_attachment', 0)} 个")

    @Property(bool, notify=changed)
    def stopping(self):
        return getattr(self, "_stopping", False)

    @Property(str, notify=changed)
    def lastPdf(self):
        return getattr(self, "_last_pdf", "")

    @Property("QVariantMap", notify=latestReportChanged)
    def latestReport(self):
        latest = {}
        for row in self.reports.rows:
            match = re.search(r"周报_(\d{4}-\d{2}-\d{2})_至_(\d{4}-\d{2}-\d{2})$", row["reportName"])
            if match and match[2] > latest.get("end", "") and "attachments" not in Path(row["reportPath"]).parts:
                latest = dict(start=match[1], end=match[2], path=row["reportPath"])
        return latest

    @Property(bool, constant=True)
    def shaderSupported(self):
        return QQuickWindow.sceneGraphBackend() != "software"

    @Property(bool, notify=changed)
    def running(self):
        return self._running

    @Property(str, notify=changed)
    def state(self):
        return self._state

    @Property(str, notify=changed)
    def currentSite(self):
        return self._current

    @Property(str, notify=changed)
    def phase(self):
        return self._phase

    @Property(str, notify=changed)
    def stageSummary(self):
        labels = {"list": "列表", "detail": "正文", "llm": "模型", "attachment": "附件"}
        rows = []
        for kind, label in labels.items():
            data = self._stage_stats.get(kind, {})
            if kind == "llm":
                errors = data.get("errors", 0)
                deferred = data.get("deferred", 0)
                successes = max(0, data.get("count", 0) - errors - deferred)
                rows.append(f"模型 {successes} 成功 · {errors} 失败 · {deferred} 暂缓 · {data.get('seconds', 0):.1f} s")
            else:
                rows.append(f"{label} {data.get('count', 0)}  ·  {data.get('seconds', 0):.1f} s")
        hits = sum(data.get("cache_hits", 0) for data in self._stage_stats.values())
        return "\n".join(rows) + f"\n缓存 {hits}  ·  失败 {getattr(self, '_errors', 0)}"

    @Property(str, notify=changed)
    def currentColumn(self):
        return self._current_column

    @Property(str, notify=changed)
    def activeSources(self):
        return "\n".join(f"{name} · {phase}" for name, phase in self._active_sources.items())

    @Property(int, notify=changed)
    def done(self):
        return self._done

    @Property(int, notify=changed)
    def total(self):
        return len(self._active) if self._active else self.sources.selectedCount

    @Property(int, notify=changed)
    def pages(self):
        return self._pages

    @Property(int, notify=changed)
    def hits(self):
        return self._hits

    @Property(str, notify=changed)
    def outputPath(self):
        return self._output

    @Property(str, notify=changed)
    def elapsed(self):
        seconds = int(self._elapsed_seconds)
        return f"{seconds // 60:02}:{seconds % 60:02}"

    def add_log(self, level, message):
        self.logs.append(dict(logTime=datetime.now().strftime("%H:%M:%S"), level=level, message=message))
        self.logAdded.emit()

    @Slot()
    def clearLogs(self):
        self.logs.clear()

    @Slot()
    def chooseOutput(self):
        folder = QFileDialog.getExistingDirectory(None, "选择输出目录", self._output)
        if folder:
            self._output = folder
            self.changed.emit()

    @Slot(str)
    def openFile(self, path):
        if Path(path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            self.toast.emit("该路径尚不存在")

    @Slot(str)
    def openSite(self, url):
        if url.startswith("https://") or url.startswith("http://"):
            QDesktopServices.openUrl(QUrl(url))

    @Slot("QVariantMap")
    def saveConfig(self, options):
        pass

    @Slot()
    def refreshReports(self):
        reports = sorted(
            (p for directory in APP_DIR.glob("output*") if directory.is_dir()
             for p in directory.rglob("*.pdf")),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        self.reports.replace([dict(
            reportName=p.stem, reportPath=str(p),
            reportDate=datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            reportSize=f"{p.stat().st_size / 1024:.0f} KB",
        ) for p in reports])

    @Slot()
    def requestExit(self):
        self.closeReady.emit()

    def shutdown(self):
        pass


class Preview(Workspace):
    def __init__(self, sources):
        super().__init__(sources)
        self.timer = QTimer(self)
        self.timer.setInterval(380)
        self.timer.timeout.connect(self.advance)
        self.refreshReports()
        self.add_log("READY", "界面预览已就绪")
        self.add_log("INFO", f"已载入 {sources.total} 个站点配置；未执行连通性检测")
        self.add_log("INFO", "当前为离线演示，不连接网站或大模型接口")

    @Property(bool, constant=True)
    def isDemo(self):
        return True

    @Slot(str, str, "QVariantMap")
    def start(self, start_date, end_date, options=None):
        if self._running:
            return
        if start_date > end_date:
            self.toast.emit("开始日期不能晚于结束日期")
            return
        self._active = [row for row in self.sources.rows if row["selected"]]
        if not self._active:
            self.toast.emit("请至少选择一个采集站点")
            return
        self._step = self._done = self._pages = self._hits = 0
        self._running = True
        self._state = "演示运行中"
        self._current = self._active[0]["siteName"]
        self._phase = "栏目发现"
        self.activity.clear()
        self.activity.put("start", "started", "演示任务已开始", f"{start_date} 至 {end_date}，共 {len(self._active)} 个站点")
        self.add_log("START", f"演示任务开始  {start_date} → {end_date}  ·  {len(self._active)} 个站点")
        self.changed.emit()
        self.timer.start()

    @Slot()
    def advance(self):
        if not self._running:
            return
        phases = ["栏目发现", "列表解析", "详情提取", "内容整理"]
        site_index = self._step // 4
        if site_index >= len(self._active):
            self.timer.stop()
            self._running = False
            self._state = "演示完成"
            self._phase = "流程已完成"
            self.activity.put("end", "done", "演示已结束", "本次没有访问网站，也没有生成 PDF。")
            self._current = "所有已选站点"
            self.add_log("DONE", "演示流程结束；没有发起网络请求或生成报告文件")
            self.changed.emit()
            self.toast.emit("演示已完成，未生成真实报告")
            return
        phase_index = self._step % 4
        source = self._active[site_index]
        self._current = source["siteName"]
        self._phase = phases[phase_index]
        self._pages += 5 + site_index % 7
        if phase_index == 2:
            self._hits += 2 + site_index % 4
        if phase_index == 3:
            self._done += 1
        self.activity.put("site:"+source["siteName"], "done" if phase_index == 3 else "working",
                          source["siteName"], "本站演示完成" if phase_index == 3 else "演示中：" + phases[phase_index])
        self.add_log("DEMO", f"{source['region']} · {source['department']}  /  {phases[phase_index]}" +
                     ("  ·  本站演示完成" if phase_index == 3 else ""))
        self._step += 1
        self._elapsed_seconds = self._step * self.timer.interval() / 1000
        self.changed.emit()

    @Slot()
    def stop(self):
        if not self._running:
            return
        self.timer.stop()
        self._running = False
        self._state = "已停止"
        self._phase = "演示已停止"
        self.activity.interrupt("演示已中止")
        self.activity.put("end", "paused", "演示任务已停止")
        self.add_log("STOP", "演示任务已停止")
        self.changed.emit()

    @Slot(str, str, bool)
    def fetchModels(self, base_url, api_key, verify_ssl=True):
        self._model_options = ["演示模型 · 标准", "演示模型 · 快速", "演示模型 · 深度"]
        self.modelsChanged.emit()
        self.toast.emit("已载入演示模型，未连接真实模型接口")

    def shutdown(self):
        self.timer.stop()


def install_intro_guard(window, timeout_ms=None):
    # The Qt GUI event loop remains live even if the frame-driven timeline stalls.
    guard = QTimer(window)
    guard.setObjectName("introWatchdog")
    guard.setSingleShot(True)
    guard.setInterval(timeout_ms if timeout_ms is not None else window.property("introDuration")+600)
    def sync():
        if window.property("booting"):
            guard.start()
        else:
            guard.stop()
    guard.timeout.connect(lambda: QMetaObject.invokeMethod(window, "finishIntro") if window.property("booting") else None)
    window.bootingChanged.connect(sync)
    sync()
    return guard


def launch_workspace(factory, smoke_check=None, artifacts=None):
    QQuickStyle.setStyle("Basic")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("GovPolicyWeekly")
    fonts = configure_workspace_fonts(app, ROOT / "assets" / "fonts")
    sources, backend = factory()
    source_filter = SourceFilter(sources)
    manage_filter = SourceFilter(sources)
    map_filter = SourceFilter(sources)
    log_filter = SourceFilter(backend.logs, ("logTime", "level", "message"), dynamic=True)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("icons", Icons())
    for name, value in {
        "workspaceFonts": fonts, "preview": backend, "sources": sources, "sourceFilter": source_filter,
        "manageFilter": manage_filter, "mapFilter": map_filter, "logModel": log_filter, "reportModel": backend.reports,
    }.items():
        engine.rootContext().setContextProperty(name, value)
    errors = []
    engine.warnings.connect(lambda warnings: errors.extend(warning.toString() for warning in warnings))
    engine.load(QUrl.fromLocalFile(str(UI / "Main.qml")))
    if not engine.rootObjects():
        backend.shutdown()
        return 1
    window = engine.rootObjects()[0]
    install_intro_guard(window)
    app.setApplicationDisplayName("政策周报 · 界面预览" if backend.isDemo else "政策周报")
    if smoke_check:
        QTimer.singleShot(window.property("introDuration")+200, lambda: smoke_check(app, window, backend, sources, source_filter, artifacts, errors))
    result = app.exec()
    backend.shutdown()
    controller = engine.incubationController()
    if controller:
        controller.incubateFor(100)
    import shiboken6
    for root_object in engine.rootObjects():
        shiboken6.delete(root_object)
    shiboken6.delete(engine)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--artifacts", type=Path, default=ROOT / "release-check" / "ui-preview")
    args = parser.parse_args()
    def factory():
        sources = Sources()
        return sources, Preview(sources)
    check = None
    if args.smoke_test:
        from scripts.test_ui_preview import run_checks
        check = run_checks
    return launch_workspace(factory, check, args.artifacts)


if __name__ == "__main__":
    raise SystemExit(main())
