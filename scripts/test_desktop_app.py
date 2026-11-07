"""Offline real-engine checks: local HTTP, model API, subprocess and linked PDF."""

from __future__ import annotations

import io
import json
import shutil
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import yaml


class DesktopFixture:
    key = "local-fixture-key"

    def __init__(self, root: Path):
        self.root = root.absolute()
        self.posts = []
        self.fail = False
        self.model_fail = False
        self.delay = 0
        self.requests = []
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send(self, body, status=200, mime="text/html; charset=utf-8"):
                data = body if isinstance(body, bytes) else body.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def do_GET(self):
                path = urlsplit(self.path).path
                fixture.requests.append(path)
                if path == "/v1/models":
                    if self.headers.get("Authorization") != "Bearer " + fixture.key:
                        self.send('{"error":"invalid fixture key"}', 401, "application/json")
                    else:
                        self.send(json.dumps({"data": [{"id": "fixture-standard"}, {"id": "fixture-fast"}]}), mime="application/json")
                    return
                if fixture.delay:
                    time.sleep(fixture.delay)
                if fixture.fail:
                    self.send("Fixture failure", 503)
                    return
                pages = {
                    "/": '<html><meta charset="utf-8"><a href="/updates/">文件列表</a></html>',
                    "/updates/": '''<html><meta charset="utf-8"><title>文件列表</title><ul>
                    <li><a href="/art/2026/10/18/art_1_1.html">关于张某等同志职务任免的通知</a><span>2026-10-18</span></li>
                    <li><a href="/art/2026/10/18/art_1_2.html">关于开展化工企业技术改造项目申报的通知</a><span>2026-10-18</span></li>
                    </ul></html>''',
                    "/art/2026/10/18/art_1_1.html": '''<html><meta charset="utf-8"><meta name="PubDate" content="2026-10-18">
                    <h1>关于张某等同志职务任免的通知</h1><div class="TRS_Editor">经研究决定，任命张某为本单位负责人，免去李某职务。本通知自发布之日起执行。
                    <a href="/files/attachment.pdf">附件：任免通知.pdf</a></div></html>''',
                    "/art/2026/10/18/art_1_2.html": '''<html><meta charset="utf-8"><meta name="PubDate" content="2026-10-18">
                    <h1>关于开展化工企业技术改造项目申报的通知</h1><div class="TRS_Editor">现组织化工企业申报技术改造专项资金。对符合条件的工业企业给予财政补贴。
                    企业应于规定时间提交申报材料。本通知公布新的申请条件和补贴标准。</div></html>''',
                }
                if path == "/files/attachment.pdf":
                    self.send(fixture.attachment, mime="application/pdf")
                else:
                    self.send(pages.get(path, "Not found"), 200 if path in pages else 404)

            def do_POST(self):
                payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
                fixture.posts.append(payload)
                if fixture.model_fail or self.headers.get("Authorization") != "Bearer " + fixture.key:
                    self.send("Unauthorized", 401)
                    return
                result = dict(include=True, final_category="policy", policy_subtype="通知", document_action="发布新文件",
                              is_personnel=False, is_policy=True, relevance_to_pesticide_chemical_enterprise="high",
                              related_directions=["化工/危化品", "工信/技改"], reason="本地接口测试：正式申报通知",
                              summary="化工企业技术改造项目申报及补贴。", change_points=["新增申报条件"],
                              exclude_reason="", confidence=0.98)
                content = json.dumps(result, ensure_ascii=False)
                self.send(json.dumps({"choices": [{"message": {"content": content}}], "output_text": content}), mime="application/json")

        from reportlab.pdfgen.canvas import Canvas
        stream = io.BytesIO()
        pdf = Canvas(stream)
        pdf.drawString(72, 720, "Local attachment fixture")
        pdf.save()
        self.attachment = stream.getvalue()
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        (self.root / "config").mkdir(parents=True, exist_ok=True)
        (self.root / "input").mkdir(exist_ok=True)
        data = [dict(name="本地测试站点", base_url=self.url + "/", region="国家", department="综合",
                     list_urls=[self.url + "/updates/"])]
        self.sources = self.root / "config" / "sources.yaml"
        self.sources.write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")
        from ui_preview import ROOT
        shutil.copyfile(ROOT / "config" / "keywords.yaml", self.root / "config" / "keywords.yaml")
        (self.root / "input" / "manual_urls.txt").write_text("", encoding="utf-8")

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def run_checks(app, window, backend, sources, source_filter, artifacts, warnings, fixture):
    from scripts.check_workspace_spacing import check_workspace_spacing, reveal_config_item
    from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt
    from PySide6.QtTest import QTest
    from PySide6.QtGui import QKeySequence
    from gov_report.desktop import DesktopController
    from ui_preview import Sources
    artifacts.mkdir(parents=True, exist_ok=True)
    checks = []

    def find(name):
        item = window.findChild(QObject, name)
        if item is None:
            pending = [window.contentItem()]
            seen = set()
            while pending:
                candidate = pending.pop()
                if candidate in seen:
                    continue
                seen.add(candidate)
                if candidate.objectName() == name:
                    return candidate
                pending.extend(candidate.childItems())
            raise AssertionError("Missing " + name)
        return item

    def click(name):
        item = find(name)
        reveal_config_item(window, item)
        point = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))
        QTest.qWait(100)

    def wait_for(predicate, timeout=30000):
        deadline = time.monotonic() + timeout / 1000
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(50)
        assert predicate(), "Timed out; recent log: " + repr(backend.logs.rows[-8:])

    def passed(name):
        checks.append(name)
        print("PASS:", name, flush=True)

    try:
        wait_for(lambda: not window.property("booting"))
        assert not backend.isDemo
        assert find("apiUrl").property("text") == fixture.url + "/v1"
        assert find("apiKey").property("keyHidden")
        assert find("requestInterval").property("value") == 0
        assert not find("attachments").property("checked")
        window.grabWindow().save(str(artifacts / "01-workspace.png"))
        passed("Real workspace restores configuration with masked credentials")
        check_workspace_spacing(window, artifacts)
        passed('Configuration rows and embedded controls keep their spacing at three window sizes')

        if window.property('workspaceV3'):
            assert find('workspaceSidebar').property('visible')
            click('startDate')
            QTest.qWait(180)
            assert find('startDate').property('opened')
            assert find('startDate').property('viewMonth') == 9
            window.grabWindow().save(str(artifacts / '08-calendar.png'))
            click('startDate')
            QTest.qWait(180)
            assert not find('startDate').property('opened')
            click('sitePicker')
            QTest.qWait(180)
            assert find('sourcePopup').property('visible')
            window.grabWindow().save(str(artifacts / '09-source-picker.png'))
            click('sitePicker')
            QTest.qWait(180)
            assert not find('sourcePopup').property('visible')
            click('nav3')
            assert window.property('page') == 3
            window.grabWindow().save(str(artifacts / '10-preferences.png'))
            click('nav0')
            passed('Sidebar preview routes settings and preserves calendar/source popups')

        backend.add_log('WARN', '测试警告：本条消息用于检查级别与正文的首行对齐。')
        backend.add_log('ERROR', '测试错误：' + '用于检查长消息换行后的列对齐。' * 10)
        QTest.qWait(100)
        window.grabWindow().save(str(artifacts / '01-log-alignment.png'))
        logs = find('logList')
        logs.setProperty('followTail', False)
        QMetaObject.invokeMethod(logs, 'positionViewAtBeginning')
        QTest.qWait(100)
        held_position = logs.property('contentY')
        backend.add_log('INFO', '测试新增日志时保留阅读位置')
        QTest.qWait(100)
        assert abs(logs.property('contentY') - held_position) < 1
        logs.setProperty('followTail', True)
        passed('Aligned log columns render long messages and preserve manual scroll position')

        find("apiUrl").setProperty("text", fixture.url)
        click("fetchModels")
        wait_for(lambda: not backend.modelsLoading and len(backend.modelOptions) == 2)
        wait_for(lambda: find("modelBox").property("currentIndex") >= 0)
        assert find("apiUrl").property("text") == fixture.url + "/v1"
        assert "/models" in fixture.requests and "/v1/models" in fixture.requests
        assert not any("演示模型" in name for name in backend.modelOptions)
        find("modelBox").setProperty("currentIndex", 0)
        click("startButton")
        wait_for(lambda: backend.running)
        window.grabWindow().save(str(artifacts / "02-running.png"))
        wait_for(lambda: not backend.running, 60000)
        assert backend.state == "已完成", backend.logs.rows[-10:]
        assert backend.done == 1 and backend.pages >= 4 and backend.hits == 2
        assert fixture.posts, "The actual LLM client did not call the local model API"
        assert fixture.posts[0]["model"] in backend.modelOptions
        pdf_path = Path(backend.lastPdf)
        pdf = pdf_path.read_bytes()
        assert pdf.startswith(b"%PDF-") and (fixture.url + "/art/2026/10/18/art_1_1.html").encode() in pdf
        data = json.loads((pdf_path.parent / "data.json").read_text(encoding="utf-8"))
        assert len(data) == 2 and any(row["decision_source"] == "大模型复判" for row in data)
        summary = json.loads((pdf_path.parent / "runtime_summary.json").read_text(encoding="utf-8"))
        assert summary["workers"] == 3 and summary["stages"]["list"]["count"] >= 2
        assert summary["stages"]["detail"]["count"] == 2
        assert summary["llm"]["success_count"] == 1 and summary["llm"]["failure_count"] == 0
        assert "/files/attachment.pdf" not in fixture.requests
        assert "缓存" in backend.stageSummary
        wait_for(lambda: backend.reports.rowCount() > 0)
        assert any(row["reportPath"] == backend.lastPdf for row in backend.reports.rows)
        QTest.qWait(200)
        window.grabWindow().save(str(artifacts / "03-completed.png"))
        assert all(fixture.key not in row["message"] for row in backend.logs.rows)
        passed("Real subprocess: crawl, model, progress, linked PDF and history; attachments default off")

        requests_before = len(fixture.requests)
        calls_before = len(fixture.posts)
        click('nav1')
        QTest.qWait(350)
        assert window.findChild(QObject, 'checkSites') is None
        assert window.findChild(QObject, 'accessDialog') is None
        assert not hasattr(backend, 'checkSelectedSites')
        sources.toggle(0)
        assert sources.selectedCount == sources.total - 1
        sources.toggle(0)
        assert sources.selectedCount == sources.total
        assert len(fixture.requests) == requests_before and len(fixture.posts) == calls_before
        window.grabWindow().save(str(artifacts / '11-sites.png'))
        click('nav0')
        QTest.qWait(200)
        passed('Site management retains selection without access checks or network requests')

        find("attachments").setProperty("checked", True)
        click("startButton")
        wait_for(lambda: backend.running)
        wait_for(lambda: not backend.running, 60000)
        assert backend.state == "已完成", backend.logs.rows[-10:]
        previous_pdf = pdf_path
        pdf_path = Path(backend.lastPdf)
        assert pdf_path != previous_pdf and previous_pdf.is_file(), "New tasks must preserve previous reports"
        assert list(pdf_path.parent.rglob("attachments/**/*.pdf"))
        manifest = json.loads((pdf_path.parent / "attachment_downloads.json").read_text(encoding="utf-8"))
        assert manifest and manifest[0]["attachments"][0]["local_path"]
        assert "/files/attachment.pdf" in fixture.requests
        assert len(fixture.posts) == 1, "Repeated input should reuse the shared model cache"
        passed("Opt-in attachment download runs after PDF export and writes its manifest")

        click("testModel")
        assert find("modelTestDialog").property("visible")
        before_posts = len(fixture.posts)
        QMetaObject.invokeMethod(find("modelTestDialog"), "accept")
        wait_for(lambda: not backend.modelTesting and "调用通过" in backend.modelTestResult)
        assert len(fixture.posts) > before_posts, "Probe must bypass cached classifications"
        passed("Model probe requires confirmation and exercises the real subprocess transport without cache")

        fixture.model_fail = True
        before_posts = len(fixture.posts)
        click("testModel")
        QMetaObject.invokeMethod(find("modelTestDialog"), "accept")
        wait_for(lambda: not backend.modelTesting and "调用失败" in backend.modelTestResult)
        assert len(fixture.posts) == before_posts + 1
        assert "401" in backend.modelTestResult
        passed("Real model probe distinguishes authorization failure from success")

        find("attachments").setProperty("checked", False)
        find("modelBox").setProperty("currentIndex", 1)
        click("startButton")
        wait_for(lambda: backend.running)
        wait_for(lambda: not backend.running, 60000)
        assert backend.state == "报告已生成（采集不完整）", backend.logs.rows[-10:]
        assert backend._coverage["counts"]["llm_failed"] == 1
        failed_task_path = backend._task_path
        fixture.model_fail = False
        before_requests = list(fixture.requests)
        click("taskCoverage")
        assert find("coverageDialog").property("visible")
        find("coverageDialog").setProperty("expandedSource", "本地测试站点")
        QTest.qWait(100)
        window.grabWindow().save(str(artifacts / "05-coverage-partial.png"))
        click("retryModelFailures")
        wait_for(lambda: backend.running)
        wait_for(lambda: not backend.running, 60000)
        assert backend._task_path == failed_task_path
        assert backend.state == "已完成" and backend.hits == 2, backend.logs.rows[-10:]
        assert fixture.requests == before_requests, "Model-only recovery must not refetch website pages"
        assert backend._coverage["counts"]["llm_failed"] == 0
        passed("Incomplete model review is visible; model-only retry preserves records without website requests")

        find("apiKey").setProperty("text", "wrong-local-key")
        click("fetchModels")
        wait_for(lambda: not backend.modelsLoading)
        assert any("401" in row["message"] for row in backend.logs.rows)
        find("apiKey").setProperty("text", fixture.key)
        wait_for(lambda: backend.store.load().get("openai_api_key") == fixture.key)
        passed("Model authentication failure is reported without replacing the cached model list")

        saved = backend.store.load()
        assert saved["openai_base_url"] == fixture.url + "/v1"
        assert saved["openai_api_key"] == fixture.key
        assert saved["openai_model"] in backend.modelOptions
        assert saved["selected_sources"] == ["本地测试站点"]
        restored = DesktopController(Sources(fixture.sources), backend.store, fixture.root)
        assert restored.initialSettings["openai_api_key"] == fixture.key
        assert restored.modelOptions == backend.modelOptions
        assert not restored.initialSettings["download_attachments"]
        assert restored.hasTask and restored._coverage["complete"] == 1
        restored.shutdown()
        passed("Atomic configuration persistence and restart restore")

        fixture.delay = 8
        click("startButton")
        wait_for(lambda: backend.running)
        wait_for(lambda: bool(backend._coverage))
        click("nav1")
        assert window.property("page") == 1
        click("nav0")
        window.requestActivate()
        QTest.qWait(150)
        QTest.keySequence(window, QKeySequence(QKeySequence.StandardKey.Close))
        QTest.qWait(150)
        assert find("exitDialog").property("visible") and backend.running
        QMetaObject.invokeMethod(find("exitDialog"), "reject")
        click("startButton")
        wait_for(lambda: not backend.running, 15000)
        assert backend.state == "已停止" and backend.process.poll() is not None
        assert not backend.lastPdf
        fixture.delay = 0
        passed("UI stays responsive during collection; exit confirmation and subprocess stop")

        click("taskCoverage")
        click("resumeTask")
        wait_for(lambda: backend.running)
        wait_for(lambda: not backend.running, 60000)
        assert backend.state == "已完成" and backend.hits == 2, backend.logs.rows[-10:]
        passed("Stopped task resumes from the persisted task file")

        before = backend.process
        backend.start("2026-10-20", "2026-10-01", {})
        assert not backend.running and backend.process is before
        sources.selectAll(False)
        backend.start("2026-10-01", "2026-10-20", {})
        assert not backend.running and backend.process is before
        sources.selectAll(True)
        passed("Invalid date range and empty source selection never launch a worker")

        window.setWidth(1020)
        window.setHeight(740)
        QTest.qWait(200)
        click('nav1')
        QTest.qWait(200)
        window.grabWindow().save(str(artifacts / '11-sites-minimum.png'))
        click('nav0')
        QTest.qWait(200)
        window.grabWindow().save(str(artifacts / "06-minimum-workspace.png"))
        if window.property('workspaceV3'):
            inspector = find('taskInspector')
            monitor = find('monitorColumn')
            assert monitor.width() <= inspector.width(), (monitor.width(), inspector.width())
            for name in ('startDate', 'endDate', 'apiUrl', 'apiKey', 'startButton'):
                item = find(name)
                point = item.mapToScene(QPointF(0, 0))
                assert point.x() >= 0 and point.x() + item.width() <= window.width() + 1, name
            passed('Compact workspace keeps control bounds inside the minimum viewport')
        QMetaObject.invokeMethod(find("coverageDialog"), "open")
        QTest.qWait(100)
        window.grabWindow().save(str(artifacts / "07-minimum-coverage.png"))
        QMetaObject.invokeMethod(find("coverageDialog"), "close")
        window.setWidth(1280)
        window.setHeight(900)

        click("nav2")
        QTest.qWait(250)
        window.grabWindow().save(str(artifacts / "04-history.png"))
        assert not warnings, warnings
        passed("QML pages and report history render without warnings")
        app.setQuitOnLastWindowClosed(False)
        window.requestActivate()
        QTest.qWait(150)
        QTest.keySequence(window, QKeySequence(QKeySequence.StandardKey.Close))
        QTest.qWait(150)
        assert not window.isVisible(), 'Standard close shortcut must close the idle window'
        passed('Standard close shortcut confirms during collection and closes the idle window')
        (artifacts / "checks.json").write_text(json.dumps({"ok": True, "checks": checks}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Desktop integration checks passed: {len(checks)}", flush=True)
        app.exit(0)
    except Exception:
        traceback.print_exc()
        window.grabWindow().save(str(artifacts / "failure.png"))
        (artifacts / "checks.json").write_text(json.dumps({"ok": False, "checks": checks, "error": traceback.format_exc(),
                                                         "warnings": warnings}, ensure_ascii=False, indent=2), encoding="utf-8")
        app.exit(1)
