"""Create a local Mac app launcher; the project and Python environment stay external."""

from __future__ import annotations

import argparse
import plistlib
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


ROOT = Path(__file__).resolve().parents[1]
IDENTIFIER = "local.govpolicyweekly.ui-preview"


def create_icon(destination: Path) -> None:
    app = QGuiApplication.instance() or QGuiApplication([])
    with tempfile.TemporaryDirectory(prefix="policy-preview-icon-") as temporary:
        iconset = Path(temporary) / "Preview.iconset"
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                pixels = size * scale
                image = QImage(pixels, pixels, QImage.Format_ARGB32_Premultiplied)
                image.fill(Qt.transparent)
                painter = QPainter(image)
                painter.setRenderHint(QPainter.Antialiasing)
                painter.setPen(Qt.NoPen)
                painter.setBrush(QColor("#a1e4cb"))
                painter.drawRoundedRect(QRectF(pixels * 0.08, pixels * 0.08, pixels * 0.84, pixels * 0.84), pixels * 0.19, pixels * 0.19)
                svg = QSvgRenderer(str(ROOT / "ui" / "preview" / "icons" / "file-text.svg"))
                painter.save()
                painter.translate(pixels * 0.24, pixels * 0.23)
                svg.render(painter, QRectF(0, 0, pixels * 0.52, pixels * 0.54))
                painter.restore()
                painter.end()
                suffix = "@2x" if scale == 2 else ""
                if not image.save(str(iconset / f"icon_{size}x{size}{suffix}.png")):
                    raise RuntimeError("Could not render the preview icon")
        subprocess.run(["/usr/bin/iconutil", "-c", "icns", str(iconset), "-o", str(destination)], check=True)
    # Retain the application through the rendering work above.
    assert app is not None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path)
    parser.add_argument("--production", action="store_true", help="Launch the functional desktop app instead of the offline preview")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("This local launcher is only for macOS")
    name = "政策周报" if args.production else "政策周报预览"
    entry = "desktop_app.py" if args.production else "ui_preview.py"
    identifier = "local.govpolicyweekly.desktop" if args.production else IDENTIFIER
    destination = (args.destination or Path.home() / "Desktop" / (name + ".app")).expanduser().absolute()
    if destination.suffix != ".app":
        parser.error("Destination must end in .app")
    if destination.exists():
        parser.error(f"Destination already exists; nothing was overwritten: {destination}")
    python = Path(sys.executable).absolute()
    if not (ROOT / entry).is_file():
        parser.error("The UI preview source is missing")

    contents = destination / "Contents"
    executable = contents / "MacOS" / "PolicyWeeklyPreview"
    resources = contents / "Resources"
    executable.parent.mkdir(parents=True)
    resources.mkdir()
    with (contents / "Info.plist").open("wb") as handle:
        plistlib.dump({
            "CFBundleIdentifier": identifier,
            "CFBundleName": name,
            "CFBundleDisplayName": name,
            "CFBundleExecutable": executable.name,
            "CFBundleIconFile": "Preview.icns",
            "CFBundlePackageType": "APPL",
            "CFBundleShortVersionString": "0.2.0",
            "CFBundleVersion": "2",
            "LSMinimumSystemVersion": "12.0",
            "NSHighResolutionCapable": True,
        }, handle, sort_keys=False)
    executable.write_text(
        "#!/bin/zsh\n"
        f"PROJECT={shlex.quote(str(ROOT))}\n"
        f"PYTHON={shlex.quote(str(python))}\n"
        f"ENTRY={shlex.quote(entry)}\n"
        'LOG_DIR="$HOME/Library/Logs/GovPolicyWeekly"\n'
        '/bin/mkdir -p "$LOG_DIR" || exit 1\n'
        'exec >> "$LOG_DIR/preview.log" 2>&1\n'
        'cd "$PROJECT" || exit 1\n'
        'if [[ ! -x "$PYTHON" || ! -f "$ENTRY" ]]; then\n'
        '    print -u2 "The preview project or Python environment has moved or is missing."\n'
        '    exit 1\n'
        'fi\n'
        'exec "$PYTHON" "$PROJECT/$ENTRY" "$@"\n',
        encoding="utf-8",
    )
    executable.chmod(0o755)
    create_icon(resources / "Preview.icns")
    print(f"Created local launcher: {destination}")
    print(f"Uses project: {ROOT}")
    print(f"Uses Python: {python}")


if __name__ == "__main__":
    main()
