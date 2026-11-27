"""Check the first native Show event, before the usual desktop smoke checks."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


def probe(reduced):
    from PySide6.QtCore import QEvent, QObject, QTimer
    from PySide6.QtWidgets import QApplication
    from gov_report.desktop import DesktopController, SettingsStore
    from ui_preview import Sources, launch_workspace

    shows = []

    class FirstWindow(QObject):
        def eventFilter(self, obj, event):
            if obj.objectName() == "previewWindow" and event.type() == QEvent.Show and not shows:
                shows.append((obj.property("settingsReady"), obj.property("booting"), obj.property("reveal")))
                QTimer.singleShot(60, lambda: self.check_frame(obj))
            return False

        def check_frame(self, window):
            image = window.grabWindow()
            ok = not image.isNull() and ((image.pixelColor(5, 5).lightness() > 160) == reduced)
            print("first show:", shows, "first frame matches:", ok, flush=True)
            QApplication.instance().exit(0 if ok and shows == [(True, not reduced, int(reduced))] else 1)

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        def factory():
            app = QApplication.instance()
            app.startup_probe = FirstWindow(app)
            app.installEventFilter(app.startup_probe)
            QTimer.singleShot(8000, lambda: app.exit(2))
            sources = Sources()
            store = SettingsStore(root/"settings.json", root/"no-legacy")
            store.save(dict(output_root=str(root/"reports"), reduced_motion=reduced))
            return sources, DesktopController(sources, store)

        return launch_workspace(factory)


class StartupOrderTests(unittest.TestCase):
    def test_first_show_uses_saved_motion_preference(self):
        for mode in ("motion", "reduced"):
            with self.subTest(mode=mode):
                result = subprocess.run(
                    [sys.executable, str(Path(__file__).resolve()), mode],
                    env=dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software"),
                    cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=30,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(probe(sys.argv[1] == "reduced"))
