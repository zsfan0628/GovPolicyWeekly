"""Capture repeatable startup frames without network access or user settings."""
import json
from pathlib import Path

from PySide6.QtCore import QMetaObject, QObject, QPointF, Qt
from PySide6.QtTest import QTest
from ui_preview import Sources, Preview, launch_workspace


def capture(app, window, backend, sources, source_filter, artifacts, warnings):
    try:
        artifacts.mkdir(parents=True, exist_ok=True)
        assert len(json.loads(backend.introMapJson)) > 1000
        assert sum(p['china'] for p in json.loads(backend.introMapJson)) > 50
        QMetaObject.invokeMethod(window, 'finishIntro')
        window.setWidth(1280); window.setHeight(800)
        window.setProperty('booting', True)
        samples = {}
        for frame in range(91):
            t = frame / 30
            p = min(1, t / 2.4)
            d = max(0, min(1, (t-2.4)/0.6))
            d = 4*d*d*d if d < .5 else 1-(-2*d+2)**3/2
            window.setProperty('glyphReveal', p)
            window.setProperty('logoTravel', d)
            window.setProperty('reveal', d)
            QTest.qWait(40)
            shot = window.grabWindow().scaledToWidth(960, Qt.SmoothTransformation)
            assert not shot.isNull()
            shot.save(str(artifacts / f'{frame:03d}.png'))
            if frame in (18, 35, 65, 82):
                samples[frame] = shot
        assert samples[18] != samples[35] and samples[35] != samples[65]
        for frame in (18, 35, 65):
            shot = samples[frame]
            colors = {shot.pixelColor(x,y).name() for x in range(120,840,3) for y in range(120,450,3)}
            assert len(colors) > 20, (frame, len(colors))
        target = window.findChild(QObject, 'brandTitle').mapToScene(QPointF(0,3))
        title = window.findChild(QObject, 'introSolidTitle').mapToScene(QPointF(0,0))
        assert abs(target.x()-title.x()) < 2 and abs(target.y()-title.y()) < 2, (target, title)
        QMetaObject.invokeMethod(window, 'finishIntro')
        assert not window.property('booting')
        assert not warnings, warnings
        print('PASS: world and China particles, title formation, transition frames and skip state')
        app.exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        app.exit(1)


if __name__ == '__main__':
    def factory():
        sources = Sources()
        return sources, Preview(sources)
    raise SystemExit(launch_workspace(factory, capture, Path('release-check/map-intro-frames')))
