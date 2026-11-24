import "Pearl.js" as Pearl
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: view
    objectName: "siteMapView"
    property bool reducedMotion: false
    property string query: ""
    property string activeRegion: "国家"
    property real entrance: 0
    readonly property var locations: sources.mapLocations
    onLocationsChanged: {
        if (!locations.some(p => p.region === activeRegion)) activeRegion = locations.length ? locations[0].region : ""
        if (connectors) connectors.requestPaint()
    }
    readonly property bool searching: query.trim().length > 0
    readonly property bool mapReady: outline.status === Image.Ready
    readonly property var counts: sources.regionCounts
    readonly property var currentCounts: counts[activeRegion] || {total:0, selected:0}
    readonly property var activeLocation: locations.filter(p => p.region === activeRegion)[0] || {title:"全部地区", city:"", lon:0, lat:0}
    function syncFilter() { mapFilter.region = query.trim().length > 0 ? "" : activeRegion; mapFilter.query = query }
    function point(location) {
        return Qt.point(outline.x + ((location.lon - 70) * 0.82 / 57.4) * outline.width,
                        outline.y + ((56 - location.lat) / 41) * outline.height)
    }
    onQueryChanged: syncFilter()
    onActiveRegionChanged: { syncFilter(); if (connectors) connectors.requestPaint() }
    onWidthChanged: connectors.requestPaint()
    onHeightChanged: connectors.requestPaint()
    onEntranceChanged: connectors.requestPaint()
    onVisibleChanged: { if (visible) { entrance = reducedMotion ? 1 : 0; appear.restart() } }
    Component.onCompleted: { syncFilter(); appear.start() }
    NumberAnimation { id: appear; target: view; property: "entrance"; to: 1; duration: view.reducedMotion ? 0 : 700; easing.type: Easing.OutCubic }

    RowLayout {
        anchors.fill: parent; spacing: 0
        Item {
            id: mapArea; objectName: "mapArea"
            Layout.fillWidth: true; Layout.fillHeight: true; clip: true
            Layout.minimumWidth: 300; Layout.preferredWidth: 740
            Image {
                source: "assets/world-outline.svg"; anchors.centerIn: parent
                width: parent.width * 1.6; height: width / 2; opacity: 0.34
                sourceSize.width: 1800
            }
            Canvas {
                anchors.fill: parent; opacity: 0.5
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const c = getContext("2d"); c.reset(); c.strokeStyle = Pearl.soft; c.lineWidth = 0.5
                    for (let x = 0; x < width; x += 48) { c.beginPath(); c.moveTo(x,0); c.lineTo(x,height); c.stroke() }
                    for (let y = 0; y < height; y += 48) { c.beginPath(); c.moveTo(0,y); c.lineTo(width,y); c.stroke() }
                }
            }
            Column {
                x: 20; y: 16; spacing: 8
                Text { text: "采集版图"; font.pixelSize: 20; font.weight: Font.Medium; color: Pearl.active }
                Text { text: "CHINA / SOURCE NETWORK"; font.pixelSize: 10; color: Pearl.muted }
            }
            Image {
                id: outline; objectName: "chinaOutline"
                source: "assets/china-region.svg"
                width: Math.min(mapArea.width * 0.93, (mapArea.height - 115) * 1.4)
                height: width / 1.4
                x: (mapArea.width - width) / 2; y: (mapArea.height - height) / 2 + 16
                sourceSize.width: 1600; opacity: view.entrance
                scale: 0.96 + 0.04 * view.entrance
                onXChanged: connectors.requestPaint()
                onYChanged: connectors.requestPaint()
                onWidthChanged: connectors.requestPaint()
            }
            Canvas {
                id: connectors; objectName: "mapConnectors"; anchors.fill: parent
                onPaint: {
                    const c=getContext("2d"); c.reset()
                    for (const loc of view.locations) {
                        const p=view.point(loc), x=mapArea.width*loc.lx, y=mapArea.height*loc.ly+24
                        const end=x < p.x ? x+100 : x
                        c.globalAlpha=view.entrance; c.strokeStyle=loc.region===view.activeRegion?Pearl.accent:Pearl.frame
                        c.lineWidth=loc.region===view.activeRegion?1.6:0.8
                        c.beginPath(); c.moveTo(p.x,p.y); c.lineTo(p.x+(end-p.x)*0.45,y); c.lineTo(end,y); c.stroke()
                    }
                    if (!view.locations.length || view.searching) return
                    const p=view.point(view.activeLocation)
                    c.strokeStyle=Pearl.frame; c.setLineDash([3,5]); c.lineWidth=1
                    c.beginPath(); c.moveTo(p.x,p.y); c.lineTo(width-18,p.y); c.lineTo(width-18,100); c.lineTo(width,100); c.stroke()
                }
            }
            Repeater {
                model: view.locations
                delegate: Item {
                    required property var modelData
                    anchors.fill: parent
                    readonly property bool active: view.activeRegion === modelData.region
                    Rectangle {
                        readonly property point location: view.point(modelData)
                        x: location.x - width/2; y: location.y - height/2
                        width: active ? 22 : 14; height: width; radius: width/2
                        color: active ? Pearl.line : Pearl.soft; border.color: active ? Pearl.accent : Pearl.frame
                        Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: active ? Pearl.accent : Pearl.frame }
                        opacity: view.entrance
                        MouseArea { anchors.fill: parent; anchors.margins: -6; cursorShape: Qt.PointingHandCursor; onClicked: view.activeRegion = modelData.region }
                    }
                    AbstractButton {
                        id: regionButton; objectName: "mapRegion" + modelData.region
                        x: mapArea.width*modelData.lx; y: mapArea.height*modelData.ly
                        width: 106; height: 49; hoverEnabled: true
                        Accessible.name: modelData.title
                        onClicked: view.activeRegion = modelData.region
                        background: Rectangle {
                            radius: 5; color: active ? Pearl.paper : regionButton.hovered ? Pearl.paper : Pearl.soft
                            border.color: active ? Pearl.frame : Pearl.line
                        }
                        padding: 0
                        contentItem: Item {
                            Column {
                                anchors.left: parent.left; anchors.leftMargin: 9; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                                Text { text: modelData.title; width: regionButton.width - 18; elide: Text.ElideRight; font.pixelSize: 13; font.weight: active ? Font.DemiBold : Font.Normal; color: Pearl.active }
                                Text { text: (view.counts[modelData.region] || {total:0}).total + " 个站点"; font.pixelSize: 10; color: Pearl.muted }
                            }
                        }
                        opacity: view.entrance
                    }
                }
            }
            Row {
                x: 20; anchors.bottom: parent.bottom; anchors.bottomMargin: 20; spacing: 8
                Rectangle { width: 6; height: 6; radius: 3; color: Pearl.accent; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "地区代表点 · 非机关办公地址"; font.pixelSize: 10; color: Pearl.muted }
            }
            Text { anchors.right: parent.right; anchors.rightMargin: 16; anchors.bottom: parent.bottom; anchors.bottomMargin: 20
                text: "区域示意 / Natural Earth"; font.pixelSize: 9; color: Pearl.frame }
        }
        Rectangle { Layout.fillHeight: true; width: 1; color: Pearl.line }
        ColumnLayout {
            id: sitePanel; objectName: "mapSitePanel"
            Layout.preferredWidth: view.width < 1050 ? 320 : 360
            Layout.minimumWidth: Layout.preferredWidth
            Layout.maximumWidth: Layout.preferredWidth
            Layout.fillHeight: true; Layout.leftMargin: 22; spacing: 12
            RowLayout {
                Layout.fillWidth: true; Layout.topMargin: 16
                ColumnLayout {
                    Layout.fillWidth: true; spacing: 5
                    Text { text: view.searching ? "搜索结果" : view.activeLocation.title; font.pixelSize: 20; color: Pearl.active; font.weight: Font.Medium }
                    Text { text: view.searching || !view.activeRegion ? siteList.count + " 个匹配站点" : view.activeLocation.city + " · 已选 " + view.currentCounts.selected + " / " + view.currentCounts.total
                        font.pixelSize: 11; color: Pearl.muted }
                }
                CheckControl {
                    objectName: "mapSelectRegion"; text: "本地区"; visible: !view.searching && !!view.activeRegion
                    checked: view.currentCounts.total > 0 && view.currentCounts.selected === view.currentCounts.total
                    partial: view.currentCounts.selected > 0 && !checked
                    enabled: !preview.running && view.currentCounts.total > 0
                    onClicked: sources.selectRegion(view.activeRegion, view.currentCounts.selected !== view.currentCounts.total)
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: Pearl.line }
            ListView {
                id: siteList; objectName: "mapSiteList"
                Layout.fillWidth: true; Layout.fillHeight: true; clip: true; spacing: 0
                model: mapFilter
                ScrollBar.vertical: ScrollBar { width: 6 }
                delegate: Item {
                    id: siteRow; objectName: "mapSite" + siteId
                    required property int siteId; required property string siteName; required property string siteUrl
                    required property string region; required property string department; required property int channels; required property bool selected
                    width: siteList.width - 10; height: 76
                    Rectangle { x: 0; width: 1; height: parent.height; color: Pearl.line }
                    Rectangle { x: 0; y: 30; width: 14; height: 1; color: Pearl.frame }
                    RowLayout {
                        anchors { fill: parent; leftMargin: 18; rightMargin: 0 }
                        spacing: 10
                        CheckControl { objectName: "mapCheck" + siteId; checked: selected; Layout.preferredWidth: 20; enabled: !preview.running; onClicked: sources.toggle(siteId) }
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 0; spacing: 5
                            Text { text: siteName; font.pixelSize: 12; font.weight: Font.Medium; color: Pearl.active; Layout.fillWidth: true; elide: Text.ElideRight
                                ToolTip.visible: nameHover.hovered; ToolTip.text: siteName; HoverHandler { id: nameHover } }
                            Text {
                                text: siteUrl.replace(/^https?:\/\//, "").replace(/\/$/, ""); color: Pearl.muted; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight
                                ToolTip.visible: urlMouse.containsMouse; ToolTip.text: siteUrl
                                MouseArea { id: urlMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: preview.openSite(siteUrl) }
                            }
                            Text { text: (view.searching ? region + " · " : "") + department + " · " + channels + " 个入口"; font.pixelSize: 10; color: Pearl.frame }
                        }
                        AppButton { objectName: "mapOpen" + siteId; iconName: "arrow-up-right"; compact: true; tone: "ghost"; hint: "打开 " + siteUrl; onClicked: preview.openSite(siteUrl) }
                    }
                    Rectangle { anchors.bottom: parent.bottom; x: 18; width: parent.width - 18; height: 1; color: Pearl.soft }
                }
                Text { anchors.centerIn: parent; visible: siteList.count===0; text: "没有匹配的站点"; color: Pearl.muted; font.pixelSize: 12 }
            }
        }
    }
}
