"""Geometry checks for the live QML workspace, without network requests."""

from PySide6.QtCore import QObject, QPointF
from PySide6.QtTest import QTest


def reveal_config_item(window, item):
    scroll = window.findChild(QObject, 'configScroll')
    content = window.findChild(QObject, 'configContent')
    ancestor = item
    while ancestor and ancestor is not content:
        ancestor = ancestor.parentItem()
    if ancestor is None:
        return
    flick = scroll.property('contentItem')
    top = item.mapToItem(content, QPointF(0, 0)).y() + content.y()
    current = flick.property('contentY')
    target = current
    if top < current + 12:
        target = top - 12
    elif top + item.height() > current + flick.height() - 12:
        target = top + item.height() - flick.height() + 12
    maximum = max(0, flick.property('contentHeight') - flick.height())
    flick.setProperty('contentY', min(maximum, max(0, target)))
    QTest.qWait(100)


def check_workspace_spacing(window, artifacts):
    def item(name):
        found = window.findChild(QObject, name)
        assert found is not None, name
        return found

    def rect(control):
        point = control.mapToScene(QPointF(0, 0))
        return point.x(), point.y(), point.x() + control.width(), point.y() + control.height()

    original_size = window.width(), window.height()
    scroll = item('configScroll').property('contentItem')
    original_y = scroll.property('contentY')
    for width, height in ((1020, 740), (1280, 900), (1440, 960)):
        window.setWidth(width)
        window.setHeight(height)
        scroll.setProperty('contentY', 0)
        QTest.qWait(300)
        content = item('configContent')
        rows = sorted((row for row in content.childItems() if row.isVisible() and row.height() > 0),
                      key=lambda row: row.y())
        for previous, following in zip(rows, rows[1:]):
            gap = following.y() - previous.y() - previous.height()
            assert gap >= 11.5, (width, previous.objectName(), following.objectName(), gap)
        for section, controls in (
            ('dateSection', ('recent7Days', 'recent30Days')),
            ('runtimeSection', ('requestInterval',)),
        ):
            bounds = rect(item(section))
            for name in controls:
                control = rect(item(name))
                assert control[1] >= bounds[1] - 0.5 and control[3] <= bounds[3] + 0.5, (section, name, bounds, control)
        for above, below in (('recent30Days', 'endDate'), ('requestInterval', 'verifySsl')):
            assert rect(item(below))[1] - rect(item(above))[3] >= 11.5, (width, above, below)
        for top, bottom in (('attachments', 'browserFallback'), ('verifySsl', 'strictMode')):
            assert rect(item(bottom))[1] - rect(item(top))[3] >= 7.5
        for name in ('startDate', 'endDate', 'apiUrl', 'apiKey', 'requestInterval', 'ruleFallback'):
            bounds = rect(item(name))
            container = rect(content)
            assert bounds[0] >= container[0] - 0.5 and bounds[2] <= container[2] + 0.5, (width, name)
        window.grabWindow().save(str(artifacts / f'spacing-{width}-top.png'))
        reveal_config_item(window, item('ruleFallback'))
        window.grabWindow().save(str(artifacts / f'spacing-{width}-settings.png'))
        bottom = rows[-1].y() + rows[-1].height() + content.y()
        assert scroll.property('contentHeight') >= bottom, 'Bottom of configuration is unreachable'
    window.setWidth(original_size[0])
    window.setHeight(original_size[1])
    scroll.setProperty('contentY', original_y)
    QTest.qWait(300)
