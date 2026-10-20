"""Interaction checks for the isolated Qt Quick preview, invoked by its launcher."""

import datetime as dt
import json
import traceback

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QPoint, QPointF, Qt
from PySide6.QtTest import QTest


def run_checks(app, window, backend, sources, source_filter, artifacts, warnings):
    artifacts.mkdir(parents=True, exist_ok=True)
    checks = []

    def find(name):
        found = window.findChild(QObject, name)
        if found:
            return found
        seen = set()
        pending = [window.contentItem()]
        while pending:
            item = pending.pop()
            if item in seen:
                continue
            seen.add(item)
            if item.objectName() == name:
                return item
            pending.extend(item.childItems())
        raise AssertionError(f"Missing UI object: {name}")

    def click(item, x=None, y=None):
        point = item.mapToScene(QPointF(
            item.width() / 2 if x is None else x,
            item.height() / 2 if y is None else y,
        ))
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(round(point.x()), round(point.y())))
        QTest.qWait(180)

    def invoke(obj, method, *args):
        result = QMetaObject.invokeMethod(obj, method, *[Q_ARG("QVariant", arg) for arg in args])
        assert result, method
        QTest.qWait(180)

    def capture(name):
        QTest.qWait(220)
        image = window.grabWindow()
        assert not image.isNull(), "Blank window capture"
        assert image.save(str(artifacts / (name + ".png")))
        # Reject a uniformly blank renderer independently of the screenshot file.
        colors = {image.pixelColor(x, y).name() for x in range(0, image.width(), 40)
                  for y in range(0, image.height(), 40)}
        assert len(colors) > 12, f"Blank or incomplete render: {name}"

    def passed(name):
        checks.append(name)
        print("PASS:", name, flush=True)

    try:
        for _ in range(80):
            if not window.property("booting"):
                break
            QTest.qWait(50)
        assert not window.property("booting")
        assert window.property("wallpaperReady"), "Bundled wallpaper did not load"
        capture("01-workspace")
        passed("Startup finishes and desktop workspace renders")

        navigation = find("mainNavigation")
        if backend.shaderSupported:
            assert not navigation.property("materialFailed"), navigation.property("materialLog")
            normal = window.grabWindow()
        lens = find("navigationLens")
        initial_x = lens.property("x")
        click(find("nav1"))
        assert lens.property("x") > initial_x + 20, "Glass selection lens did not move"
        QTest.qWait(600)
        click(find("nav0"))
        QTest.qWait(600)
        assert abs(lens.property("x") - initial_x) < 1
        window.setProperty("reducedTransparency", True)
        capture("11-reduced-transparency")
        assert window.property("reducedTransparency")
        if backend.shaderSupported:
            opaque = window.grabWindow()
            ratio = normal.width() / window.width()
            corner = navigation.mapToScene(QPointF(0, 0))
            differences = 0
            for x in range(20, int(navigation.width()) - 20, 16):
                for y in range(8, int(navigation.height()) - 8, 6):
                    px, py = round((corner.x() + x) * ratio), round((corner.y() + y) * ratio)
                    if normal.pixelColor(px, py) != opaque.pixelColor(px, py):
                        differences += 1
            assert differences > 50, "Glass output is indistinguishable from its opaque fallback"
            window.setProperty("reducedTransparency", False)
        passed("Rendered glass material, animated navigation lens and opaque fallback")

        seven = find("recent7Days")
        thirty = find("recent30Days")
        end = dt.date.today() - dt.timedelta(days=1)
        assert seven.property("selected") and not thirty.property("selected")
        click(thirty)
        assert thirty.property("selected") and not seven.property("selected")
        assert find("startDate").property("value") == (end - dt.timedelta(days=29)).isoformat()
        assert find("endDate").property("value") == end.isoformat()
        assert thirty.property("background").property("color").name() == "#e5f0e9"
        capture("12-recent-30-selected")
        click(thirty)
        assert thirty.property("selected"), "Clicking the active preset must not deselect it"
        find("endDate").setProperty("value", (end - dt.timedelta(days=1)).isoformat())
        assert not seven.property("selected") and not thirty.property("selected")
        find("endDate").setProperty("value", end.isoformat())
        assert thirty.property("selected"), "Restored dates must restore the matching preset"
        click(seven)
        assert seven.property("selected") and not thirty.property("selected")
        assert find("startDate").property("value") == (end - dt.timedelta(days=6)).isoformat()
        capture("13-recent-7-selected")
        passed("Date presets show exclusive selection, retain repeated clicks and follow manual dates")

        date = find("startDate")
        click(date, date.width() - 15)
        assert date.property("opened")
        capture("02-calendar")
        click(date, date.width() - 15)
        assert not date.property("opened"), "Calendar arrow must toggle closed"
        click(date)
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(450, 60))
        QTest.qWait(200)
        assert not date.property("opened"), "Outside click must dismiss calendar"
        click(date)
        month = date.property("viewMonth")
        invoke(date, "shiftMonth", -1)
        assert date.property("viewMonth") != month
        old_value = date.property("value")
        click(find("startDateDay15"))
        assert not date.property("opened") and date.property("value") != old_value
        passed("Calendar arrow, outside dismissal, month navigation and date selection")

        picker = find("sitePicker")
        # Scroll configuration down on compact displays if necessary.
        click(picker)
        assert picker.property("opened")
        popup = find("sourcePopup")
        top = picker.mapToScene(QPointF(0, popup.property("y"))).y()
        assert top >= 0 and top + popup.property("height") <= window.height(), "Popup extends outside window"
        source_list = find("sourcePopupList")
        source_list.setProperty("contentY", 0.0)
        wheel_point = source_list.mapToScene(QPointF(100, 80))
        QTest.wheelEvent(window, wheel_point, QPoint(0, -360))
        QTest.qWait(300)
        assert source_list.property("contentY") > 0, "Source list must respond to mouse wheel"
        source_list.setProperty("contentY", source_list.property("contentHeight") - source_list.height())
        QTest.qWait(200)
        before = source_list.property("contentY")
        click(find("siteRow29"))
        QTest.qWait(250)
        assert sources.selectedCount == 29
        assert abs(source_list.property("contentY") - before) < 2, "Source list jumped after selection"
        assert not find("allSourcesCheck").property("checked")
        assert find("allSourcesCheck").property("partial")
        capture("03-site-picker")
        search = find("sourceSearch")
        search.setProperty("text", "江苏")
        QTest.qWait(200)
        assert source_list.property("count") == 6
        sources.selectAll(False)
        assert sources.selectedCount == 0
        click(find("allSourcesCheck"))
        assert sources.selectedCount == 30, "Select all must affect all 30, not only filtered rows"
        search.setProperty("text", "")
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(500, 60))
        QTest.qWait(200)
        assert not picker.property("opened")
        click(picker)
        click(picker)
        assert not picker.property("opened")
        click(picker)
        QTest.keyClick(window, Qt.Key_Escape)
        QTest.qWait(180)
        assert not picker.property("opened")
        passed("Bounded source popup, mouse wheel, real row selection, partial/all/none and stable scroll")

        api_key = find("apiKey")
        api_key.setProperty("text", "preview-test-key")
        assert api_key.property("keyHidden")
        click(find("revealKey"))
        assert not api_key.property("keyHidden")
        click(find("revealKey"))
        api_key.setProperty("text", "")
        click(find("fetchModels"))
        assert find("modelBox").property("count") == 3
        passed("Masked key toggle and explicit demo model selector")

        click(find("startButton"))
        assert backend.running
        backend.timer.stop()
        for _ in range(14):
            backend.advance()
        capture("04-running")
        assert backend.done > 0 and backend.pages > 0
        logs = find("logList")
        for index in range(60):
            backend.add_log("DEMO", f"日志滚动检查 {index:02d}")
        QTest.qWait(250)
        assert logs.property("atYEnd")
        logs.setProperty("followTail", False)
        logs.setProperty("contentY", 30.0)
        QTest.qWait(100)
        before = logs.property("contentY")
        backend.add_log("DEMO", "新日志不能改变向上查看的位置")
        QTest.qWait(250)
        assert abs(logs.property("contentY") - before) < 2
        assert not logs.property("atYEnd")
        logs.setProperty("followTail", True)
        invoke(logs, "positionViewAtEnd")
        QTest.wheelEvent(window, logs.mapToScene(QPointF(130, 40)), QPoint(0, 240))
        QTest.qWait(250)
        assert not logs.property("followTail") and not logs.property("atYEnd")
        before = logs.property("contentY")
        backend.add_log("DEMO", "真实滚轮回看时保持位置")
        QTest.qWait(200)
        assert abs(logs.property("contentY") - before) < 2
        log_search = find("logSearch")
        log_search.setProperty("text", "不能改变")
        QTest.qWait(150)
        assert logs.property("count") == 1
        log_search.setProperty("text", "")
        click(find("startButton"))
        assert not backend.running
        passed("Start/stop demo, live counters, log tail-follow and retained scroll position")

        click(find("nav1"))
        assert window.property("page") == 1
        find("manageSearch").setProperty("text", "湖北")
        QTest.qWait(150)
        assert find("manageList").property("count") == 6
        find("manageSearch").setProperty("text", "")
        capture("05-sites")
        click(find("nav2"))
        assert window.property("page") == 2
        capture("06-reports")
        click(find("nav3"))
        assert window.property("page") == 3
        capture("07-settings")
        click(find("nav0"))
        passed("All four pages and source-management filtering")

        window.resize(1020, 740)
        capture("08-compact")
        assert window.width() == 1020 and window.height() == 740
        window.resize(1280, 900)
        window.setProperty("reducedMotion", True)
        invoke(window, "replayIntro")
        assert not window.property("booting")
        window.setProperty("reducedMotion", False)
        QMetaObject.invokeMethod(window, "replayIntro")
        intro_frames = artifacts / "intro-frames"
        intro_frames.mkdir(exist_ok=True)
        for frame in range(30):
            QTest.qWait(60)
            captured = window.grabWindow()
            captured.scaledToWidth(960, Qt.SmoothTransformation).save(str(intro_frames / f"{frame:03d}.png"))
            if frame == 3:
                assert window.property("booting")
                captured.save(str(artifacts / "09-intro-start.png"))
            if frame == 13:
                captured.save(str(artifacts / "10-intro-transition.png"))
        QTest.qWait(500)
        assert not window.property("booting")
        QMetaObject.invokeMethod(window, "replayIntro")
        QTest.qWait(160)
        click(find("skipIntro"))
        assert not window.property("booting") and window.property("reveal") == 1
        passed("Compact viewport, particle startup, reduced-motion and skip action")

        # A one-site run must reach a real terminal state without producing files.
        sources.selectAll(False)
        sources.toggle(0)
        backend.start("2026-10-01", "2026-10-07")
        backend.timer.stop()
        for _ in range(5):
            backend.advance()
        assert backend.state == "演示完成" and backend.done == 1
        before_count = len(backend.logs.rows)
        backend.start("2026-10-08", "2026-10-01")
        assert not backend.running and len(backend.logs.rows) == before_count
        sources.selectAll(True)
        passed("Completed demo and invalid date-range validation")

        assert not warnings, "QML warnings:\n" + "\n".join(warnings)
        passed("No QML warnings or renderer errors")
        (artifacts / "checks.json").write_text(json.dumps({"passed": checks, "warnings": warnings}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Preview checks passed: {len(checks)}. Screenshots: {artifacts}", flush=True)
        app.exit(0)
    except Exception:
        traceback.print_exc()
        window.grabWindow().save(str(artifacts / "failure.png"))
        (artifacts / "failure.json").write_text(json.dumps({"passed": checks, "warnings": warnings, "error": traceback.format_exc()}, ensure_ascii=False, indent=2), encoding="utf-8")
        app.exit(1)
