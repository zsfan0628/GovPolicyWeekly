"""Offline interaction and screenshot checks for the site map."""
from pathlib import Path

from PySide6.QtCore import QObject, QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from ui_preview import Sources, Preview, launch_workspace


def checks(app, window, backend, sources, source_filter, artifacts, warnings):
    artifacts.mkdir(parents=True, exist_ok=True)
    def find(name):
        obj = window.findChild(QObject, name)
        if obj is not None:
            return obj
        pending = [window.contentItem()]
        while pending:
            obj = pending.pop()
            if obj.objectName() == name:
                return obj
            pending.extend(obj.childItems())
        raise AssertionError(name)

    def click(name):
        obj = find(name)
        p = obj.mapToScene(QPointF(obj.width()/2, obj.height()/2))
        QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, QPoint(round(p.x()), round(p.y())))
        QTest.qWait(250)

    try:
        for _ in range(80):
            if not window.property('booting'):
                break
            QTest.qWait(50)
        assert not window.property('booting')
        click('nav1')
        QTest.qWait(800)
        assert find('siteMapView').property('mapReady')
        assert find('mapSiteList').property('count') == 6
        bar = find('siteViewMode')
        for tab in ('mapViewTab', 'listViewTab'):
            button = find(tab)
            p = button.mapToItem(bar, QPointF(0,0))
            assert abs(p.y() - (bar.height()-p.y()-button.height())) < 0.5
            assert p.y() == 3 and button.height() == 30, (p.y(), button.height())
            assert button.property('background').height() == button.height()
        bar_rect = bar.mapToScene(QPointF(0,0))
        screenshot = window.grabWindow()
        ratio = screenshot.width() / window.width()
        screenshot.copy(round((bar_rect.x()-10)*ratio), round((bar_rect.y()-10)*ratio),
                        round((bar.width()+20)*ratio), round((bar.height()+20)*ratio)).save(str(artifacts / 'button-map.png'))
        for name in ('mapArea', 'mapSitePanel', 'mapSiteList', 'mapSite0', 'mapOpen0'):
            obj = find(name)
            point = obj.mapToScene(QPointF(0,0))
            assert point.x() + obj.width() <= window.width(), name
        window.grabWindow().save(str(artifacts / '01-national.png'))
        click('mapRegion湖北')
        assert find('mapSiteList').property('count') == 6
        ids = [row['siteId'] for row in sources.rows if row['region'] == '湖北']
        click('mapCheck' + str(ids[0]))
        assert sources.selectedCount == 29
        assert sources.regionCounts['湖北']['selected'] == 5
        click('mapSelectRegion')
        assert sources.selectedCount == 30
        click('mapSelectRegion')
        assert sources.regionCounts['湖北']['selected'] == 0
        click('mapSelectRegion')
        window.grabWindow().save(str(artifacts / '02-hubei.png'))
        find('manageSearch').setProperty('text', '财政')
        QTest.qWait(250)
        assert find('mapSiteList').property('count') == 5, (find('mapSiteList').property('count'), find('siteMapView').property('query'), find('siteMapView').property('searching'))
        click('listViewTab')
        screenshot = window.grabWindow()
        screenshot.copy(round((bar_rect.x()-10)*ratio), round((bar_rect.y()-10)*ratio),
                        round((bar.width()+20)*ratio), round((bar.height()+20)*ratio)).save(str(artifacts / 'button-list.png'))
        assert find('manageList').property('count') == 5
        find('manageSearch').setProperty('text', '')
        click('mapViewTab')
        assert find('mapSiteList').property('count') == 6
        for w,h in ((1020,740),(1440,960)):
            window.setWidth(w); window.setHeight(h); QTest.qWait(400)
            area = find('mapArea')
            for region in ('国家','黑龙江','江苏','湖北','南通'):
                button = find('mapRegion' + region)
                assert 0 <= button.x() and button.x()+button.width() <= area.width()
                assert 0 <= button.y() and button.y()+button.height() <= area.height()
            window.grabWindow().save(str(artifacts / f'03-map-{w}.png'))
        assert not warnings, warnings
        print('PASS: map assets, 5 regions, selection, region all/none, search, list sync and viewport bounds')
        app.exit(0)
    except Exception:
        import traceback
        traceback.print_exc()
        window.grabWindow().save(str(artifacts / 'failure.png'))
        app.exit(1)


if __name__ == '__main__':
    def factory():
        sources = Sources()
        return sources, Preview(sources)
    raise SystemExit(launch_workspace(factory, checks, Path('release-check/site-map')))
