"""Install the two bundled font families for this application process only."""
from pathlib import Path

from PySide6.QtGui import QFont, QFontDatabase


def configure_workspace_fonts(app, directory: Path) -> dict[str, str]:
    families = app.property("workspaceFontFamilies")
    if not families:
        families = {}
        for role, filename in (
            ("sans", "SourceHanSansCN-Regular.ttf"),
            ("sans", "SourceHanSansCN-Medium.ttf"),
            ("sans", "SourceHanSansCN-Bold.ttf"),
            ("serif", "SourceHanSerifCN-SemiBold.otf"),
        ):
            font_id = QFontDatabase.addApplicationFont(str((directory / filename).resolve()))
            names = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
            if not names:
                raise RuntimeError(f"无法加载内置字体 {filename}，请检查软件文件是否完整")
            families.setdefault(role, names[0])
        app.setProperty("workspaceFontFamilies", families)
    app.setFont(QFont(families["sans"], 13))
    return families
