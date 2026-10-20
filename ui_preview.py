"""Independent, offline design preview. Does not start the collection engine."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import yaml
from PySide6.QtCore import (
    QAbstractListModel, QModelIndex, QObject, Property, QSortFilterProxyModel,
    QRectF, Qt, QTimer, QUrl, Signal, Slot,
)
from PySide6.QtGui import QColor, QDesktopServices, QFont, QImage, QPainter
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


class Sources(Rows):
    selectionChanged = Signal()

    def __init__(self, path=None):
        sources = yaml.safe_load(Path(path or ROOT / "config" / "sources.yaml").read_text(encoding="utf-8"))
        self.source_data = sources
        regions = ["国家", "江苏", "湖北", "黑龙江", "南通"]
        sources = sorted(sources, key=lambda row: regions.index(row["region"]) if row.get("region") in regions else len(regions))
        rows = [dict(
            siteId=i, siteName=row["name"], region=row.get("region", ""),
            department=row.get("department", ""), siteUrl=row["base_url"],
            channels=len(row.get("list_urls", [])), selected=True,
        ) for i, row in enumerate(sources)]
        super().__init__(rows, ["siteId", "siteName", "region", "department", "siteUrl", "channels", "selected"])

    @Property(int, notify=selectionChanged)
    def selectedCount(self):
        return sum(row["selected"] for row in self.rows)

    @Property(int, constant=True)
    def total(self):
        return len(self.rows)

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
        return self._query.strip().lower() in " ".join(
            str(source[key]) for key in self._fields
        ).lower()


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
        mask = QImage(720, 160, QImage.Format_ARGB32_Premultiplied)
        mask.fill(Qt.transparent)
        painter = QPainter(mask)
        font = QFont("PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei UI")
        font.setPixelSize(140)
        font.setWeight(QFont.DemiBold)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(QRectF(0, 0, 720, 160), Qt.AlignCenter, "政策周报")
        painter.end()
        points = [(x, y) for y in range(4, mask.height(), 3) for x in range(4, mask.width(), 3)
                  if mask.pixelColor(x, y).alpha() > 130]
        points = points[::max(1, len(points) // 2400)]
        left = min(x for x, _ in points); right = max(x for x, _ in points)
        top = min(y for _, y in points); bottom = max(y for _, y in points)
        self._intro_points_json = json.dumps([dict(x=(x - left) / max(1, right - left), y=(y - top) / max(1, bottom - top))
                                             for x, y in points])
        self.logs = Rows([], ["logTime", "level", "message"])
        self.reports = Rows([], ["reportName", "reportPath", "reportDate", "reportSize"])
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

    @Property(bool, constant=True)
    def isDemo(self):
        return False

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
    def stopping(self):
        return getattr(self, "_stopping", False)

    @Property(str, notify=changed)
    def lastPdf(self):
        return getattr(self, "_last_pdf", "")

    @Property(str, constant=True)
    def introPointsJson(self):
        return self._intro_points_json

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
        self.add_log("STOP", "演示任务已停止")
        self.changed.emit()

    @Slot(str, str, bool)
    def fetchModels(self, base_url, api_key, verify_ssl=True):
        self._model_options = ["演示模型 · 标准", "演示模型 · 快速", "演示模型 · 深度"]
        self.modelsChanged.emit()
        self.toast.emit("已载入演示模型，未连接真实模型接口")

    def shutdown(self):
        self.timer.stop()


def launch_workspace(factory, smoke_check=None, artifacts=None):
    QQuickStyle.setStyle("Basic")
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName("GovPolicyWeekly")
    app.setFont(QFont("PingFang SC" if sys.platform == "darwin" else "Microsoft YaHei UI", 13))
    sources, backend = factory()
    source_filter = SourceFilter(sources)
    manage_filter = SourceFilter(sources)
    log_filter = SourceFilter(backend.logs, ("logTime", "level", "message"), dynamic=True)
    engine = QQmlApplicationEngine()
    engine.addImageProvider("icons", Icons())
    for name, value in {
        "preview": backend, "sources": sources, "sourceFilter": source_filter,
        "manageFilter": manage_filter, "logModel": log_filter, "reportModel": backend.reports,
    }.items():
        engine.rootContext().setContextProperty(name, value)
    errors = []
    engine.warnings.connect(lambda warnings: errors.extend(warning.toString() for warning in warnings))
    engine.load(QUrl.fromLocalFile(str(UI / "Main.qml")))
    if not engine.rootObjects():
        backend.shutdown()
        return 1
    window = engine.rootObjects()[0]
    app.setApplicationDisplayName("政策周报 · 界面预览" if backend.isDemo else "政策周报")
    if smoke_check:
        QTimer.singleShot(2200, lambda: smoke_check(app, window, backend, sources, source_filter, artifacts, errors))
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
