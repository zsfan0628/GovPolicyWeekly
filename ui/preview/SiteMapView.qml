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
    property var locations: [
        {region:"国家", title:"国家部门", city:"北京", lon:116.40, lat:39.90, lx:0.08, ly:0.27},
        {region:"黑龙江", title:"黑龙江", city:"哈尔滨", lon:126.64, lat:45.75, lx:0.71, ly:0.14},
        {region:"江苏", title:"江苏", city:"南京", lon:118.80, lat:32.06, lx:0.72, ly:0.45},
        {region:"湖北", title:"湖北", city:"武汉", lon:114.30, lat:30.59, lx:0.10, ly:0.67},
        {region:"南通", title:"南通", city:"南通", lon:120.86, lat:32.01, lx:0.73, ly:0.75}
    ]
    readonly property bool searching: query.trim().length > 0
    readonly property bool mapReady: outline.status === Image.Ready
    readonly property var counts: sources.regionCounts
    readonly property var currentCounts: counts[activeRegion] || {total:0, selected:0}
    readonly property var activeLocation: locations.filter(p => p.region === activeRegion)[0]
    function syncFilter() { mapFilter.region = query.trim().length > 0 ? "" : activeRegion; mapFilter.query = query }
    function point(location) {
        return Qt.point(outline.x + ((location.lon - 70) * 0.82 / 57.4) * outline.width,
                        outline.y + ((56 - location.lat) / 41) * outline.height)
    }
    onQueryChanged: syncFilter()
    onActiveRegionChanged: { syncFilter(); connectors.requestPaint() }
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
                    const c = getContext("2d"); c.reset(); c.strokeStyle = "#e0e9e4"; c.lineWidth = 0.5
                    for (let x = 0; x < width; x += 48) { c.beginPath(); c.moveTo(x,0); c.lineTo(x,height); c.stroke() }
                    for (let y = 0; y < height; y += 48) { c.beginPath(); c.moveTo(0,y); c.lineTo(width,y); c.stroke() }
                }
            }
            Column {
                x: 20; y: 16; spacing: 8
                Text { text: "采集版图"; font.pixelSize: 20; font.weight: Font.Medium; color: "#254b43" }
                Text { text: "CHINA / SOURCE NETWORK"; font.pixelSize: 10; color: "#7b9087" }
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
                        c.globalAlpha=view.entrance; c.strokeStyle=loc.region===view.activeRegion?"#368973":"#a2b9af"
                        c.lineWidth=loc.region===view.activeRegion?1.6:0.8
                        c.beginPath(); c.moveTo(p.x,p.y); c.lineTo(p.x+(end-p.x)*0.45,y); c.lineTo(end,y); c.stroke()
                    }
                    const p=view.point(view.activeLocation)
                    c.strokeStyle="#8db3a4"; c.setLineDash([3,5]); c.lineWidth=1
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
                        color: active ? "#d3e7dd" : "#edf5ef"; border.color: active ? "#64a18d" : "#a2b9af"
                        Rectangle { anchors.centerIn: parent; width: 6; height: 6; radius: 3; color: active ? "#297b61" : "#86a396" }
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
                            radius: 5; color: active ? "#fafffc" : regionButton.hovered ? "#f3f8f5" : "#eaf2ee"
                            border.color: active ? "#80ad9c" : "#dbe7df"
                        }
                        padding: 0
                        contentItem: Item {
                            Column {
                                anchors.left: parent.left; anchors.leftMargin: 9; anchors.verticalCenter: parent.verticalCenter; spacing: 4
                                Text { text: modelData.title; font.pixelSize: 13; font.weight: active ? Font.DemiBold : Font.Normal; color: "#294e42" }
                                Text { text: (view.counts[modelData.region] || {total:0}).total + " 个站点"; font.pixelSize: 10; color: "#7b8d84" }
                            }
                        }
                        opacity: view.entrance
                    }
                }
            }
            Row {
                x: 20; anchors.bottom: parent.bottom; anchors.bottomMargin: 20; spacing: 8
                Rectangle { width: 6; height: 6; radius: 3; color: "#31846b"; anchors.verticalCenter: parent.verticalCenter }
                Text { text: "地区代表点 · 非机关办公地址"; font.pixelSize: 10; color: "#7c8d85" }
            }
            Text { anchors.right: parent.right; anchors.rightMargin: 16; anchors.bottom: parent.bottom; anchors.bottomMargin: 20
                text: "区域示意 / Natural Earth"; font.pixelSize: 9; color: "#98a79f" }
        }
        Rectangle { Layout.fillHeight: true; width: 1; color: "#dce7df" }
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
                    Text { text: view.searching ? "搜索结果" : view.activeLocation.title; font.pixelSize: 20; color: "#274c40"; font.weight: Font.Medium }
                    Text { text: view.searching ? siteList.count + " 个匹配站点" : view.activeLocation.city + " · 已选 " + view.currentCounts.selected + " / " + view.currentCounts.total
                        font.pixelSize: 11; color: "#84918a" }
                }
                CheckControl {
                    objectName: "mapSelectRegion"; text: "本地区"; visible: !view.searching
                    checked: view.currentCounts.total > 0 && view.currentCounts.selected === view.currentCounts.total
                    partial: view.currentCounts.selected > 0 && !checked
                    enabled: !preview.running && view.currentCounts.total > 0
                    onClicked: sources.selectRegion(view.activeRegion, view.currentCounts.selected !== view.currentCounts.total)
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#dce7df" }
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
                    Rectangle { x: 0; width: 1; height: parent.height; color: "#c7dace" }
                    Rectangle { x: 0; y: 30; width: 14; height: 1; color: "#91b5a3" }
                    RowLayout {
                        anchors { fill: parent; leftMargin: 18; rightMargin: 0 }
                        spacing: 10
                        CheckControl { objectName: "mapCheck" + siteId; checked: selected; Layout.preferredWidth: 20; enabled: !preview.running; onClicked: sources.toggle(siteId) }
                        ColumnLayout {
                            Layout.fillWidth: true; Layout.minimumWidth: 0; Layout.preferredWidth: 0; spacing: 5
                            Text { text: siteName; font.pixelSize: 12; font.weight: Font.Medium; color: "#345145"; Layout.fillWidth: true; elide: Text.ElideRight
                                ToolTip.visible: nameHover.hovered; ToolTip.text: siteName; HoverHandler { id: nameHover } }
                            Text {
                                text: siteUrl.replace(/^https?:\/\//, "").replace(/\/$/, ""); color: "#6d8f80"; font.pixelSize: 11; Layout.fillWidth: true; elide: Text.ElideRight
                                ToolTip.visible: urlMouse.containsMouse; ToolTip.text: siteUrl
                                MouseArea { id: urlMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: preview.openSite(siteUrl) }
                            }
                            Text { text: (view.searching ? region + " · " : "") + department + " · " + channels + " 个入口"; font.pixelSize: 10; color: "#94a198" }
                        }
                        AppButton { objectName: "mapOpen" + siteId; iconName: "arrow-up-right"; compact: true; tone: "ghost"; hint: "打开 " + siteUrl; onClicked: preview.openSite(siteUrl) }
                    }
                    Rectangle { anchors.bottom: parent.bottom; x: 18; width: parent.width - 18; height: 1; color: "#e5ece7" }
                }
                Text { anchors.centerIn: parent; visible: siteList.count===0; text: "没有匹配的站点"; color: "#7c8e82"; font.pixelSize: 12 }
            }
        }
    }
}
