from __future__ import annotations

import datetime as dt
import json
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
        from PySide6.QtWidgets import QApplication
        from openpyxl import load_workbook

        from gov_report.date_utils import resolve_date_range
        from gov_report.report import export_docx, export_excel, export_pdf_direct
        from qt_app import GovPolicyQtApp

        start, end = resolve_date_range(start_date="2026-06-01", end_date="2026-06-07")
        assert start.utcoffset() == dt.timedelta(hours=8)
        checks.append("cli_imports_and_shanghai_timezone")

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
        result["ok"] = True
    except Exception:
        result["error"] = traceback.format_exc()

    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if result["ok"] else 1
