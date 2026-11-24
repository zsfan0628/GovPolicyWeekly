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
        assert sum(a.pixel(x,y)!=b.pixel(x,y) for x in range(a.width()) for y in range(a.height())) <= .02*a.width()*a.height()

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
        assert 60 <= frames <= 108
        for frame in range(frames):
            pose(frame/(frames-1))
            shot = window.grabWindow().scaledToWidth(960,Qt.SmoothTransformation)
            assert not shot.isNull() and shot.save(str(artifacts/f'{frame:03d}.png'))
            if frame in (9,35,59,frames-1):
                samples.append(shot)
        assert all(a!=b for a,b in zip(samples,samples[1:]))
        pose(.12)
        world,flow = find('introGrainWorld'),find('introGrainFlow')
        assert find('introWorldWide').property('sourceSize').width()==2256 and world.isVisible() and world.opacity()==1
        assert flow.opacity()==0 and flow.property('sourceSize').width()==3760
        assert window.grabWindow().save(str(artifacts.parent/'map-native.png'))
        pose(.40)
        china,camera = find('introGrainChina'),find('introCamera')
        assert world.isVisible() and world.opacity()==1 and china.opacity()==1 and flow.opacity()==0
        assert find('introWorldClose').opacity()==1 and find('introWorldClose').property('sourceSize').width()==2256
        assert china.property('sourceSize').width()==2256 and abs(camera.scale()-2.12)<.01
        focus = window.grabWindow()
        assert focus.save(str(artifacts.parent/'china-native.png'))
        # Actual map ink must remain visible west of China, even outside the original tile.
        small = focus.scaledToWidth(960,Qt.SmoothTransformation)
        assert sum(small.pixelColor(x,y).red()<237 for x in range(15,90)
                   for y in range(small.height()//4,small.height()//2))>15
        pose(.60)
        assert 0<world.opacity()<1 and not china.isVisible() and flow.isVisible() and 0<flow.property('frame')<29
        pose(.79)
        assert not flow.isVisible() and find('introTitle').opacity()==1
        check_dock()
        assert window.grabWindow().scaledToWidth(960,Qt.SmoothTransformation).save(str(artifacts/f'{frames:03d}.png'))
        for w,h in ((1020,740),(1440,960)):
            window.setProperty('booting',True)
            guard.stop()
            window.resize(w,h)
            QTest.qWait(160)
            find('startDate').setProperty('value','2026-11-16')
            pose(.52)
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
        print("PASS: single grain map and title morph, date independence, brand handoff at 3 widths, stalled-intro recovery, Escape and reduced motion")
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
