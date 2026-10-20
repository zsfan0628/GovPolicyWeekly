import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: navigation
    property int currentIndex: 0
    property bool reducedMotion: false
    property bool reducedTransparency: false
    property var texture: null
    property Item scene: null
    readonly property bool materialFailed: surface.shaderFailed
    readonly property string materialLog: surface.renderLog
    signal chosen(int index)
    implicitWidth: 488; implicitHeight: 58
    readonly property real segmentWidth: (width - 12) / 4
    GlassSurface {
        id: surface
        anchors.fill: parent
        texture: navigation.texture; scene: navigation.scene
        radius: height / 2; frost: 6; whiteMix: 0.62
        reducedTransparency: navigation.reducedTransparency
        light: Qt.point(hover.point.position.x / width, hover.point.position.y / height)
    }
    GlassSurface {
        id: lens
        objectName: "navigationLens"
        x: 6 + navigation.currentIndex * navigation.segmentWidth
        y: 6; width: navigation.segmentWidth; height: navigation.height - 12
        texture: navigation.texture; scene: navigation.scene
        radius: height / 2; frost: 2; thickness: 20; whiteMix: 0.84
        reducedTransparency: navigation.reducedTransparency
        Behavior on x { enabled: !navigation.reducedMotion; SpringAnimation { spring: 5; damping: 0.38; mass: 0.9; epsilon: 0.15 } }
    }
    HoverHandler { id: hover }
    Row {
        x: 6; y: 6; height: navigation.height - 12
        Repeater {
            model: ["layout-dashboard", "globe", "history", "settings-2"]
            delegate: AbstractButton {
                id: nav
                required property int index
                required property string modelData
                readonly property bool active: navigation.currentIndex === index
                objectName: "nav" + index
                width: navigation.segmentWidth; height: navigation.height - 12
                hoverEnabled: true
                Accessible.name: ["采集任务", "站点管理", "历史报告", "设置"][index]
                onClicked: navigation.chosen(index)
                background: Rectangle { radius: height / 2; color: nav.hovered && !nav.active ? "#22ffffff" : "transparent"; border.width: nav.activeFocus ? 1 : 0; border.color: "#6a9d86" }
                contentItem: Item {
                    Row {
                        anchors.centerIn: parent; spacing: 7
                        scale: nav.down ? 0.96 : nav.hovered ? 1.025 : 1
                        Behavior on scale { NumberAnimation { duration: 140 } }
                        Icon { name: nav.modelData; width: 17; height: 17; tint: nav.active ? "#17684c" : "#53645a"; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: ["采集任务", "站点管理", "历史报告", "设置"][nav.index]; color: nav.active ? "#174c37" : "#526357"; font.pixelSize: 13; font.weight: nav.active ? Font.DemiBold : Font.Normal }
                    }
                }
            }
        }
    }
}
