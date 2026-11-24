"""Geometry checks for the live QML workspace, without network requests."""

from PySide6.QtCore import QObject, QPointF, Qt
from PySide6.QtTest import QTest


def reveal_config_item(window, item):
    scroll = window.findChild(QObject, 'configScroll')
    content = window.findChild(QObject, 'configContent')
    ancestor = item
    while ancestor and ancestor is not content:
        if ancestor.objectName() in ('modelDrawer','advancedDrawer') and not ancestor.isVisible():
            heading = window.findChild(QObject, ancestor.objectName().replace('Drawer','Heading'))
            reveal_config_item(window, heading)
            QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier,
                             heading.mapToScene(QPointF(heading.width()/2, heading.height()/2)).toPoint())
            QTest.qWait(120)
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
    for width, height in ((1020, 740), (1280, 900), (1440, 960)):
        window.setWidth(width)
        window.setHeight(height)
        window.setProperty('drawer', '')
        scroll.setProperty('contentY', 0)
        QTest.qWait(180)
        arc, first, last = (item(n) for n in ('horizonCalendar','startDate','endDate'))
        assert arc.property('valid') and arc.property('days') >= 1
        assert rect(arc)[3] <= rect(first)[1] and rect(first)[2] < rect(last)[0]
        assert rect(item('dateSection'))[3] <= rect(first)[1] - 8
        for a,b in [('sitePicker','modelHeading'),('modelHeading','advancedHeading')]:
            assert rect(item(b))[1] >= rect(item(a))[3]+8
        assert rect(item('modelHeading'))[0] >= rect(last)[2]+12
        assert not item('advancedDrawer').isVisible() and not item('modelDrawer').isVisible()
        window.grabWindow().save(str(artifacts / f'spacing-{width}-top.png'))
        for name in ('apiUrl','apiKey','requestInterval','ruleFallback'):
            box = item(name)
            reveal_config_item(window, box)
            left, top, right, bottom = rect(box)
            bounds = rect(item('configScroll'))
            assert box.isVisible() and left>=bounds[0]-1 and right<=bounds[2]+1, (name,bounds,rect(box))
            assert top>=bounds[1]-1 and bottom<=bounds[3]+1, (name,bounds,rect(box))
        for top,bottom in [('attachments','browserFallback'),('verifySsl','strictMode')]:
            assert rect(item(bottom))[1] >= rect(item(top))[3]+7
        window.grabWindow().save(str(artifacts / f'spacing-{width}-settings.png'))
    window.setProperty('drawer','')
    window.setWidth(original_size[0]); window.setHeight(original_size[1])
    scroll.setProperty('contentY',0)
    QTest.qWait(180)
