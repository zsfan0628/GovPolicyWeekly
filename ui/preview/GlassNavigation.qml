import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Pearl.js" as Pearl

Item {
    id: navigation
    property int currentIndex: 0
    property bool reducedMotion: false
    property bool reducedTransparency: false
    property var texture: null
    property Item scene: null
    signal chosen(int index)
    implicitWidth: 418; implicitHeight: 46
    readonly property real segmentWidth: (width - 12) / 4
    Rectangle {
        id: lens
        objectName: "navigationLens"
        x: 6 + navigation.currentIndex * navigation.segmentWidth
        y: 6; width: navigation.segmentWidth; height: navigation.height - 12
        color: Pearl.soft; radius: height / 2; antialiasing: true
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
                padding: 0
                topInset: 0; bottomInset: 0; leftInset: 0; rightInset: 0
                hoverEnabled: true
                focusPolicy: Qt.StrongFocus
                Accessible.name: ["采集任务", "站点管理", "历史报告", "设置"][index]
                onClicked: navigation.chosen(index)
                background: Rectangle {
                    radius: lens.radius; antialiasing: true
                    color: nav.hovered && !nav.active ? "#22ffffff" : "transparent"
                    border.width: nav.visualFocus ? 1 : 0; border.color: Pearl.accent
                }
                contentItem: Item {
                    Row {
                        anchors.centerIn: parent; spacing: 7
                        scale: nav.down ? 0.96 : nav.hovered ? 1.025 : 1
                        Behavior on scale { NumberAnimation { duration: 140 } }
                        Icon { name: nav.modelData; width: 17; height: 17; tint: nav.active ? Pearl.active : Pearl.muted; anchors.verticalCenter: parent.verticalCenter }
                        Text { text: ["采集任务", "站点管理", "历史报告", "设置"][nav.index]; color: nav.active ? Pearl.active : Pearl.muted; font.pixelSize: 13; font.weight: nav.active ? Font.DemiBold : Font.Normal }
                    }
                }
            }
        }
    }
}
