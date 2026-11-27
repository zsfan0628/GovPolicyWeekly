"""Capture the real Qt opening timeline, offline and with isolated settings."""
import tempfile
import traceback
from pathlib import Path

from PySide6.QtCore import QMetaObject, QObject, QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from gov_report.desktop import DesktopController, SettingsStore
from ui_preview import Sources, launch_workspace


def capture(app, window, backend, sources, source_filter, artifacts, warnings):
    def find(name):
        return window.findChild(QObject, name)

    def pose(t):
        window.setProperty('introProgress', t)
        QTest.qWait(36)

    def check_dock():
        pose(1)
        word,brand = find('introTitle'),find('brandTitle')
        for corner in (0,1):
            def position(item):
                return item.mapToScene(QPointF(corner*item.width(),corner*item.height()))
            assert (position(word)-position(brand)).manhattanLength()<.1
        top=brand.mapToScene(QPointF(0,0))
        before=window.grabWindow()
        ratio=before.width()/window.width()
        region=tuple(round(v*ratio) for v in (top.x()-2,top.y()-2,brand.width()+4,brand.height()+4))
        QMetaObject.invokeMethod(window,'finishIntro'); QTest.qWait(80)
        a=before.copy(*region)
        b=window.grabWindow().copy(*region)
        mismatch=sum(a.pixel(x,y)!=b.pixel(x,y) for x in range(a.width()) for y in range(a.height()))
        if mismatch>.02*a.width()*a.height():
            a.save(str(artifacts.parent/'dock-before.png'))
            b.save(str(artifacts.parent/'dock-after.png'))
            raise AssertionError(f'Brand handoff changed {mismatch} pixels in {region}')

    try:
        artifacts.mkdir(parents=True, exist_ok=True)
        window.resize(1160, 780)
        QMetaObject.invokeMethod(window, 'finishIntro')
        calendar = find('horizonCalendar')
        assert calendar.property('days')==7
        window.setProperty('booting', True)
        guard = find("introWatchdog")
        guard.stop()  # Recording drives the timeline manually, slower than real time.
        QTest.mouseMove(window,QPoint(4,4))
        samples = []
        frames = round(window.property('introDuration') * 60 / 1000)
        assert frames==288
        for frame in range(frames):
            pose(frame/(frames-1))
            shot = window.grabWindow().scaledToWidth(960,Qt.SmoothTransformation)
            assert not shot.isNull() and shot.save(str(artifacts/f'{frame:03d}.png'))
            if frame in (9,35,59,frames-1):
                samples.append(shot)
        assert all(a!=b for a,b in zip(samples,samples[1:]))
        assert find('introCamera') is None
        stage=find('welcomeSweep')
        def lit(x,y,w,h):
            shot=window.grabWindow()
            dpr=shot.width()/window.width()
            a=stage.mapToScene(QPointF(x,y)); b=stage.mapToScene(QPointF(x+w,y+h))
            return sum(shot.pixelColor(i,j).lightness()>48
                       for i in range(round(a.x()*dpr),round(b.x()*dpr),2)
                       for j in range(round(a.y()*dpr),round(b.y()*dpr),2))
        pose(.026)
        assert lit(25,141,14,14)>0 and lit(44,96,456,44)==0
        pose(.22)
        assert find('introRibbon').isVisible() and find('welcomeInk').isVisible()
        assert lit(44,98,70,40)>50 and lit(468,98,32,40)==0
        pose(.40)
        assert find('welcomeWord').property('text')=='Welcome to Policy Weekly'
        assert find('welcomeInk').width()==456
        settled=window.grabWindow()
        q=stage.mapToScene(QPointF(44,98))
        dpi=settled.width()/window.width()
        left=(round(q.x()*dpi),round(q.y()*dpi),round(130*dpi),round(39*dpi))
        pose(.30)  # The first letters have landed but the phrase is still forming.
        assert window.grabWindow().copy(*left)==settled.copy(*left), 'Settled strokes changed sharpness'
        pose(.465)
        assert 0<find('welcomeInk').width()<456
        pose(.62)
        spiral=find('introSpiral')
        assert spiral.isVisible() and 0<spiral.property('frame')<83 and find('welcomeInk').width()==0
        assert spiral.property('sourceSize').width()==3808
        pose(.83)
        assert not spiral.isVisible() and find('introTitle').opacity()==1
        pose(.91)
        iris=window.grabWindow()
        assert iris.pixelColor(8,8).lightness()<35
        center=iris.pixelColor(iris.width()//2,iris.height()//2)
        check_dock()
        final=window.grabWindow()
        assert center==final.pixelColor(final.width()//2,final.height()//2)
        assert window.grabWindow().scaledToWidth(960,Qt.SmoothTransformation).save(str(artifacts/f'{frames:03d}.png'))
        for w,h in ((1020,740),(1440,960)):
            window.setProperty('booting',True)
            guard.stop()
            window.resize(w,h)
            QTest.qWait(160)
            find('startDate').setProperty('value','2026-11-16')
            pose(.62)
            QTest.qWait(80)
            reference=window.grabWindow()
            find('startDate').setProperty('value','2026-10-24')
            QTest.qWait(60)
            assert calendar.property('days')==30
            other=window.grabWindow()
            assert other.size()==reference.size() and other.format()==reference.format()
            # Software antialiasing can vary slightly at the text edges.
            assert other==reference or all(abs(a-b)<=2 for a,b in zip(other.constBits(),reference.constBits())), \
                f'Date or workspace leaked into the intro at {w}x{h}'
            check_dock()
        assert calendar.isVisible() and calendar.opacity()==1
        original = guard.interval()
        guard.setInterval(100)
        window.setProperty('booting',True)  # No scene-graph animation will finish this one.
        QTest.qWait(260)
        assert not window.property('booting') and window.property('reveal')==1
        guard.setInterval(original)
        window.requestActivate()
        QMetaObject.invokeMethod(window,'replayIntro')
        QTest.qWait(130)
        QTest.keyClick(window,Qt.Key_Escape)
        QTest.qWait(60)
        assert not window.property('booting')
        window.setProperty('reducedMotion',True)
        QMetaObject.invokeMethod(window,'replayIntro')
        assert not window.property('booting')
        assert not warnings,warnings
        print("PASS: greeting, spiral, date independence, brand handoff at 3 widths, stalled-intro recovery, Escape and reduced motion")
        app.exit(0)
    except Exception:
        traceback.print_exc()
        app.exit(1)


if __name__ == '__main__':
    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        def factory():
            sources = Sources()
            store = SettingsStore(tmp/'settings.json', tmp/'no-legacy')
            store.save(dict(output_root=str(tmp/'reports'), start_date='2026-11-16', end_date='2026-11-22', use_llm=False))
            return sources, DesktopController(sources,store)
        raise SystemExit(launch_workspace(factory,capture,Path('release-check/world-mark/frames')))
