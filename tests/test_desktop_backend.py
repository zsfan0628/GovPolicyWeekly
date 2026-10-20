from __future__ import annotations

import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from PySide6.QtWidgets import QApplication

from gov_report.desktop import DesktopController, SettingsStore, fetch_model_catalogue, normalize_api_url
from ui_preview import Sources


class SettingsTests(unittest.TestCase):
    def test_migrates_legacy_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            legacy = root / "legacy.json"
            legacy.write_text('{"openai_api_key":"local-key","unknown":"preserved"}', encoding="utf-8")
            store = SettingsStore(root / "new" / "settings.json", legacy)
            data = store.load()
            self.assertEqual(data["openai_api_key"], "local-key")
            store.save({**data, "openai_model": "fixture-model"})
            self.assertEqual(store.load()["unknown"], "preserved")
            self.assertNotIn("openai_model", json.loads(legacy.read_text()))
            self.assertEqual(list(store.path.parent.glob("*.tmp")), [])
            if os.name != "nt":
                self.assertEqual(store.path.stat().st_mode & 0o077, 0)

    def test_invalid_json_and_non_object_settings_are_safe(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "settings.json"
            store = SettingsStore(path, path)
            for content in ("broken", "[]", "null"):
                path.write_text(content)
                self.assertEqual(store.load(), {})


class ModelTests(unittest.TestCase):
    def test_normalizes_supported_endpoint_suffixes(self):
        for tail in ("/", "/models", "/chat/completions", "/responses"):
            self.assertEqual(normalize_api_url("https://example.com/v1" + tail), "https://example.com/v1")
        embedded_credentials = "https://" + "user:key@" + "example.com/v1"
        for value in ("not-a-url", "file:///tmp/model", embedded_credentials, "https://example.com/v1?key=secret"):
            with self.assertRaises(ValueError):
                normalize_api_url(value)

    @patch("gov_report.desktop.requests.get")
    def test_models_are_sorted_unique_and_ssl_setting_is_passed(self, get):
        get.return_value = Mock(status_code=200)
        get.return_value.json.return_value = {"data": [{"id": "z"}, {"id": "a"}, {"id": "a"}]}
        self.assertEqual(fetch_model_catalogue("https://example.com/v1", "local-key", False), (["a", "z"], "https://example.com/v1"))
        self.assertFalse(get.call_args.kwargs["verify"])
        self.assertEqual(get.call_args.kwargs["headers"]["Authorization"], "Bearer local-key")

    @patch("gov_report.desktop.requests.get")
    def test_bare_server_falls_back_to_v1_only_on_not_found(self, get):
        good = Mock(status_code=200)
        good.json.return_value = {"data": [{"id": "fixture"}]}
        get.side_effect = [Mock(status_code=404), good]
        self.assertEqual(fetch_model_catalogue("https://example.com", "local-key", True), (["fixture"], "https://example.com/v1"))
        self.assertEqual(get.call_args.args[0], "https://example.com/v1/models")
        get.reset_mock()
        get.side_effect = None
        get.return_value = Mock(status_code=401)
        with self.assertRaisesRegex(ValueError, "401"):
            fetch_model_catalogue("https://example.com", "local-key", True)
        self.assertEqual(get.call_count, 1)


class ControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        store = SettingsStore(self.root / "settings.json", self.root / "missing")
        store.save({"use_llm": False, "output_root": str(self.root / "output")})
        self.controller = DesktopController(Sources(), store)

    def tearDown(self):
        self.controller.shutdown()
        self.temporary.cleanup()

    def test_missing_key_dates_sources_and_bad_interval_cannot_launch(self):
        controller = self.controller
        with patch("gov_report.desktop.subprocess.Popen") as popen:
            controller.start("2026-10-02", "2026-10-01", {})
            controller.start("2026-10-01", "2026-10-02", {"use_llm": True})
            controller.start("2026-10-01", "2026-10-02", {"sleep_seconds": float("nan")})
            controller.sources.selectAll(False)
            controller.start("2026-10-01", "2026-10-02", {})
            popen.assert_not_called()
        self.assertFalse(controller.running)

    def test_credentials_never_appear_in_ui_log(self):
        self.controller.saveConfig({"openai_api_key": "private-local-key"})
        self.controller.add_log("ERROR", "server echoed private-local-key")
        self.assertNotIn("private-local-key", self.controller.logs.rows[-1]["message"])

    def test_progress_is_driven_by_structured_events_not_log_text(self):
        controller = self.controller
        controller.add_log("INFO", "命中 999 条")
        self.assertEqual(controller.hits, 0)
        for event in (dict(event="source_started", source="example"), dict(event="page_processed", kind="list"),
                      dict(event="page_processed", kind="detail"), dict(event="record_included"), dict(event="source_finished")):
            controller._progress(event)
        self.assertEqual((controller.currentSite, controller.pages, controller.hits, controller.done), ("example", 2, 1, 1))

    @patch("gov_report.desktop.threading.Thread")
    @patch("gov_report.desktop.subprocess.Popen")
    def test_run_options_reach_worker_without_credentials_on_command_line(self, popen, thread):
        popen.return_value.poll.return_value = 0
        options = dict(use_llm=False, download_attachments=False, browser_fallback=False,
                       strict_mode=False, verify_ssl=False, allow_rule_fallback=True,
                       sleep_seconds=1.2, openai_api_key="worker-local-key")
        self.controller.start("2026-10-01", "2026-10-02", options)
        command = popen.call_args.args[0]
        for flag in ("--no-llm", "--no-download-attachments", "--no-browser-fallback", "--loose",
                     "--no-verify-ssl", "--allow-rule-fallback", "--progress-json"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--max-channels-per-source") + 1], "0")
        self.assertEqual(command[command.index("--max-detail-per-source") + 1], "0")
        self.assertEqual(command[command.index("--sleep") + 1], "1.2")
        self.assertNotIn("worker-local-key", " ".join(command))
        self.assertEqual(popen.call_args.kwargs["env"]["GOV_REPORT_OPENAI_API_KEY"], "worker-local-key")
        self.assertTrue(self.controller.running)

    def test_failure_or_missing_pdf_is_not_reported_as_success(self):
        controller = self.controller
        existing_pdf = self.root / "previous.pdf"
        existing_pdf.write_bytes(b"%PDF-previous-report")
        for code, payload in ((1, {"paths": {"pdf": str(existing_pdf)}}), (0, None)):
            controller._running = True
            controller._started_at = time.monotonic()
            controller._completed_payload = payload
            controller._finish(code)
            self.assertEqual(controller.state, "任务失败")
            self.assertFalse(controller.running)
            self.assertEqual(controller.lastPdf, "")


if __name__ == "__main__":
    unittest.main()
