from __future__ import annotations

import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from zipfile import ZipFile


def run_self_test(result_path: Path) -> int:
    """Exercise the packaged UI and report exporters without network requests."""
    checks = []
    result = {"ok": False, "checks": checks}
    try:
        import main
        from PySide6.QtCore import Qt
        from PySide6.QtQuickControls2 import QQuickStyle
        from PySide6.QtWidgets import QApplication
        from openpyxl import load_workbook

        from gov_report.date_utils import resolve_date_range
        from gov_report.report import export_docx, export_excel, export_pdf_direct
        from qt_app import GovPolicyQtApp

        start, end = resolve_date_range(start_date="2026-06-01", end_date="2026-06-07")
        assert start.utcoffset() == dt.timedelta(hours=8)
        checks.append("cli_imports_and_shanghai_timezone")

        QQuickStyle.setStyle("Basic")
        qt = QApplication.instance() or QApplication([])
        original_loader = GovPolicyQtApp._load_settings
        GovPolicyQtApp._load_settings = lambda self: {}
        try:
            window = GovPolicyQtApp()
        finally:
            GovPolicyQtApp._load_settings = original_loader
        window.timer.stop()
        assert window.source_list.count() > 1
        window.source_list.item(0).setCheckState(Qt.Unchecked)
        assert not window.select_all_sources.isChecked()
        assert len(window._selected_sources()) == window.source_list.count() - 1
        window.select_all_sources.setChecked(True)
        assert len(window._selected_sources()) == window.source_list.count()
        assert window.start_date.calendarPopup() and window.end_date.calendarPopup()
        window.close()
        qt.processEvents()
        checks.append("desktop_calendar_and_source_selection")
        check_glass_workspace(qt)
        checks.append("glass_workspace_and_real_controller")
        checks.append("offline_update_badge_dialog_and_apply")

        url = "https://example.com/policy?item=1&source=smoke"
        records = [{
            "publish_date": "2026-06-01",
            "source_name": "Test source",
            "category": "policy",
            "title": "Policy title & link",
            "summary": "Offline packaging check.",
            "url": url,
            "attachments": [],
        }]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            export_excel(records, root / "data.xlsx")
            workbook = load_workbook(root / "data.xlsx")
            assert workbook.active["G2"].value == records[0]["title"]
            workbook.close()
            checks.append("excel_export")

            export_docx(records, root / "report.docx", start, end, {})
            with ZipFile(root / "report.docx") as archive:
                assert b"hyperlink" in archive.read("word/document.xml")
            checks.append("word_export")

            export_pdf_direct(records, root / "report.pdf", start, end, {})
            pdf = (root / "report.pdf").read_bytes()
            assert pdf.startswith(b"%PDF-") and url.encode("ascii") in pdf
            checks.append("pdf_export_and_title_link")

            from qt_app import APP_DIR, RESOURCE_DIR

            sources_path = root / "empty-sources.yaml"
            sources_path.write_text("[]\n", encoding="utf-8")
            manual_path = root / "empty-urls.txt"
            manual_path.touch()
            worker_log = root / "worker.log"
            command = [sys.executable]
            if not getattr(sys, "frozen", False):
                command.append(str(APP_DIR / "qt_app.py"))
            command.extend([
                "--run-cli", "--start-date", "2026-06-01", "--end-date", "2026-06-07",
                "--sources", str(sources_path), "--manual-urls", str(manual_path),
                "--keywords", str(RESOURCE_DIR / "config" / "keywords.yaml"),
                "--output-root", str(root / "cli-output"), "--no-llm", "--no-browser-fallback",
            ])
            environment = os.environ.copy()
            environment["GOV_REPORT_WORKER_LOG"] = str(worker_log)
            worker = subprocess.run(command, env=environment, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=60)
            log = worker_log.read_text(encoding="utf-8") if worker_log.exists() else ""
            assert worker.returncode == 0, log or worker.stdout.decode("utf-8", errors="replace")
            assert "共命中 0 条" in log, "CLI task did not write its UTF-8 progress log"
            assert list((root / "cli-output").rglob("*.pdf")), "CLI task did not create a PDF"
            checks.append("cli_worker_progress_and_pdf")
        result["ok"] = True
    except Exception:
        result["error"] = traceback.format_exc()

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["ok"] else 1


def check_glass_workspace(application) -> None:
    from PySide6.QtCore import QEventLoop, QObject, QTimer, QUrl
    from PySide6.QtGui import QTextLayout
    from PySide6.QtQml import QQmlApplicationEngine
    from ui_preview import Icons, Sources, SourceFilter, UI, ROOT
    from gov_report.ui_fonts import configure_workspace_fonts
    from gov_report.desktop import DesktopController, SettingsStore
    from gov_report.update_ui import UpdateUI
    from gov_report.updates import RAW, LATEST
    import hashlib
    import time
    import shiboken6

    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        store = SettingsStore(root / "settings.json", root / "no-legacy")
        store.save({"use_llm": False, "reduced_motion": True, "output_root": str(root / "output")})
        fonts = configure_workspace_fonts(application, ROOT / "assets" / "fonts")
        sources = Sources()
        controller = DesktopController(sources, store)
        updates = UpdateUI(controller, controller.resource_dir/'config', root)
        controller._updater = updates
        version = updates.revision + 1
        pack = dict(schema=1, revision=version, sources=[dict(name='示例站点', department='示例部门',
                    region='浙江', base_url='https://example.gov.cn/', list_urls=[], channel_names={})],
                    scope=dict(column_names=[]), regions=[dict(region='浙江', title='浙江省', city='杭州',
                    lon=120, lat=30, lx=.55, ly=.65)])
        raw = json.dumps(pack).encode()
        sha = hashlib.sha256(raw).hexdigest()
        def offline_read(url, limit, *, output=None, **unused):
            if url == RAW+'/sites.json':
                return json.dumps(dict(schema=1, revision=version, size=len(raw), sha256=sha)).encode()
            if url == LATEST:
                return b'{"draft":true}'
            assert url == RAW+'/catalogue.json' and output is not None and limit == len(raw)
            output.write(raw)
            return len(raw), sha
        updates.read = offline_read
        source_filter = SourceFilter(sources)
        manage_filter = SourceFilter(sources)
        map_filter = SourceFilter(sources)
        log_filter = SourceFilter(controller.logs, ("logTime", "level", "message"), dynamic=True)
        engine = QQmlApplicationEngine()
        engine.addImageProvider("icons", Icons())
        warnings = []
        engine.warnings.connect(lambda items: warnings.extend(item.toString() for item in items))
        for name, value in {"workspaceFonts": fonts, "preview": controller, "sources": sources, "sourceFilter": source_filter,
                            "manageFilter": manage_filter, "mapFilter": map_filter,
                            "logModel": log_filter, "reportModel": controller.reports}.items():
            engine.rootContext().setContextProperty(name, value)
        try:
            engine.load(QUrl.fromLocalFile(str(UI / "Main.qml")))
            assert engine.rootObjects(), "Glass workspace did not load"
            window = engine.rootObjects()[0]
            loop = QEventLoop()
            QTimer.singleShot(600, loop.quit)
            loop.exec()
            assert window.findChild(QObject, "horizonCalendar").property("valid"), "Packaged calendar failed to load"
            assert window.findChild(QObject, "startButton").property("text") == "开始生成"
            assert window.findChild(QObject, "apiKey").property("keyHidden")
            assert window.findChild(QObject, "startDate").property("value")
            for name, role, sample in (("introTitle", "serif", "政策周报"),
                                       ("calendarDayCount", "serif", "730"),
                                       ("startButton", "sans", "开始生成 30 PDF")):
                item = window.findChild(QObject, name)
                if item is None:
                    # Repeater letters belong to the scene's visual tree.
                    pending = [window.contentItem()]
                    while pending:
                        candidate = pending.pop()
                        if candidate.objectName() == name:
                            item = candidate
                            break
                        pending.extend(candidate.childItems())
                assert item is not None, name
                layout = QTextLayout(sample, item.property("font"))
                layout.beginLayout()
                layout.createLine().setLineWidth(600)
                layout.endLayout()
                rendered = {run.rawFont().familyName() for run in layout.glyphRuns()}
                assert rendered == {fonts[role]}, (name, rendered, fonts[role])
            assert not window.grabWindow().isNull(), "Glass workspace rendering is blank"
            sources.toggle(0)
            assert sources.selectedCount == sources.total - 1
            def wait_update():
                deadline = time.monotonic() + 5
                while updates.busy and time.monotonic() < deadline:
                    application.processEvents()
                    time.sleep(.005)
                application.processEvents()
                assert not updates.busy, updates.status
            badge = window.findChild(QObject, 'availableUpdate')
            assert not badge.property('visible')
            updates.check()
            wait_update()
            assert badge.property('visible')
            badge.clicked.emit()
            application.processEvents()
            assert window.findChild(QObject, 'updateDialog').property('visible')
            updates.download('sites')
            wait_update()
            apply_button = window.findChild(QObject, 'applyUpdate')
            assert apply_button.property('enabled') and apply_button.property('visible'), updates.status
            apply_button.clicked.emit()
            application.processEvents()
            assert updates.revision == version and not badge.property('visible')
            assert [r['region'] for r in sources.mapLocations] == ['浙江']
            assert not warnings, "\n".join(warnings)
        finally:
            controller.shutdown()
            for obj in engine.rootObjects():
                shiboken6.delete(obj)
            shiboken6.delete(engine)
