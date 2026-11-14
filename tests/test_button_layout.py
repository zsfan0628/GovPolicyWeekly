from pathlib import Path
import unittest

from PySide6.QtCore import QObject, QPointF, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from ui_preview import Icons


class ButtonLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        QQuickStyle.setStyle('Basic')
        cls.app = QApplication.instance() or QApplication([])

    def test_command_icon_and_text_buttons_remain_centered_in_all_states(self):
        engine = QQmlEngine()
        engine.addImageProvider('icons', Icons())
        path = Path(__file__).resolve().parents[1] / 'ui/preview/AppButton.qml'
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(path)))
        self.assertEqual(component.status(), QQmlComponent.Ready, component.errorString())
        for label, icon, compact in [('开始生成', 'play', False), ('获取模型', 'refresh-cw', False),
                                     ('近 30 天', '', True), ('', 'x', True), ('测试实际调用', 'activity', False)]:
            for enabled, down in ((True, False), (True, True), (False, False)):
                with self.subTest(label=label, icon=icon, compact=compact, enabled=enabled, down=down):
                    button = component.createWithInitialProperties(dict(text=label, iconName=icon, compact=compact,
                                                                         enabled=enabled, down=down))
                    self.app.processEvents()
                    row = button.findChild(QObject, 'buttonContents')
                    pos = row.mapToItem(button, QPointF(0, 0))
                    self.assertAlmostEqual(pos.x(), button.width() - pos.x() - row.width(), delta=1)
                    self.assertAlmostEqual(pos.y(), button.height() - pos.y() - row.height(), delta=1)
                    for name in ('buttonIcon', 'buttonLabel'):
                        child = button.findChild(QObject, name)
                        if child.isVisible():
                            p = child.mapToItem(button, QPointF(0, 0))
                            self.assertAlmostEqual(p.y() + child.height()/2, button.height()/2, delta=1)
                            self.assertGreaterEqual(p.y(), 0)
                            self.assertLessEqual(p.y()+child.height(), button.height())
                    background = button.property('background')
                    self.assertEqual(background.height(), button.height())
                    self.assertEqual(background.y(), 0)
                    button.deleteLater()
        self.app.processEvents()

    def test_toggle_track_has_equal_vertical_insets_at_different_control_heights(self):
        engine = QQmlEngine()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(
            Path(__file__).resolve().parents[1] / 'ui/preview/Toggle.qml')))
        for height in (22, 30, 36):
            button = component.createWithInitialProperties({'height': height})
            self.app.processEvents()
            track = button.property('background')
            self.assertAlmostEqual(track.y(), (height-track.height())/2)
            button.deleteLater()
