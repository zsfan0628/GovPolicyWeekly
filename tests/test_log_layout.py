from pathlib import Path
import unittest

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine, QQmlExpression
from PySide6.QtQuick import QQuickItem
from PySide6.QtWidgets import QApplication


class LogLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_fixed_columns_and_first_line_baselines_across_lengths(self):
        engine = QQmlEngine()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(
            Path(__file__).resolve().parents[1] / 'ui/preview/LogRow.qml')))
        self.assertEqual(component.status(), QQmlComponent.Ready, component.errorString())
        for width in (480, 980):
            for level in ('INFO', 'READY', 'WARN', 'ERROR', 'WARNING'):
                with self.subTest(width=width, level=level):
                    row = component.createWithInitialProperties(dict(
                        logTime='17:19:15', level=level, message='测试日志内容\nhttps://example.com/' + 'a' * 240, width=width))
                    self.assertIsNotNone(row, component.errorString())
                    self.app.processEvents()
                    self.assertAlmostEqual(row.property('timeBaseline'), row.property('messageBaseline'), places=2)
                    self.assertAlmostEqual(row.property('levelBaseline'), row.property('messageBaseline'), places=2)
                    self.assertEqual(row.property('messageColumn'), 150)
                    content = row.findChild(QQuickItem, 'logMessage')
                    self.assertLessEqual(content.width() + content.x(), width)
                    self.assertGreaterEqual(row.height(), row.property('inkHeight') + 13)
                    self.assertAlmostEqual(row.property('topInset'), row.property('bottomInset'), places=2)
                    self.assertGreaterEqual(row.property('topInset'), 6)
                    row.deleteLater()
        self.app.processEvents()

    def test_single_line_and_multiline_have_balanced_visible_padding(self):
        engine = QQmlEngine()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(
            Path(__file__).resolve().parents[1] / 'ui/preview/LogRow.qml')))
        for message in ('采集工作台已就绪', 'PDF ready', 'English descenders: gjpqy',
                        '', '第一行\n第二行', '长消息自动换行' * 45):
            with self.subTest(message=message[:18]):
                row = component.createWithInitialProperties(dict(logTime='16:51:28', level='INFO', message=message, width=520))
                self.assertIsNotNone(row, component.errorString())
                self.app.processEvents()
                self.assertAlmostEqual(row.property('topInset'), row.property('bottomInset'), places=2)
                self.assertGreaterEqual(row.property('topInset'), 6)
                self.assertAlmostEqual(row.property('timeBaseline'), row.property('messageBaseline'), places=2)
                row.deleteLater()
        self.app.processEvents()

    def test_log_markup_is_displayed_as_plain_text(self):
        engine = QQmlEngine()
        component = QQmlComponent(engine, QUrl.fromLocalFile(str(
            Path(__file__).resolve().parents[1] / 'ui/preview/LogRow.qml')))
        row = component.createWithInitialProperties(dict(logTime='00:00:00', level='INFO', message='<b>literal</b>', width=600))
        self.assertIsNotNone(row, component.errorString())
        content = row.findChild(QQuickItem, 'logMessage')
        self.assertEqual(content.property('text'), '<b>literal</b>')
        expression = QQmlExpression(engine.rootContext(), content, 'Number(textFormat)')
        result = expression.evaluate()
        self.assertEqual(result[0] if isinstance(result, tuple) else result, 0)
        row.deleteLater()
        self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
