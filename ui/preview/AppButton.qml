import QtQuick
import QtQuick.Controls

Button {
    id: control
    property string iconName: ""
    property string tone: "default"
    property bool compact: false
    property string hint: ""
    implicitHeight: compact ? 30 : 36
    implicitWidth: text.length ? contentItem.implicitWidth + 26 : implicitHeight
    padding: 0
    hoverEnabled: true
    opacity: enabled ? 1 : 0.38
    Accessible.name: text || hint
    background: Rectangle {
        radius: control.tone === "primary" || control.tone === "danger" ? height / 2 : 7
        color: control.tone === "primary" ? (control.down ? "#1257b7" : control.hovered ? "#237ce9" : "#166bd5")
             : control.tone === "danger" ? (control.hovered ? "#f6dddd" : "#f9ecec")
             : control.tone === "ghost" ? (control.hovered ? "#140d3421" : "transparent")
             : control.hovered ? "#eef3ef" : "#ffffff"
        border.width: control.activeFocus ? 1 : (control.tone === "default" ? 1 : 0)
        border.color: control.activeFocus ? "#6194c2" : "#d6dfd9"
        Behavior on color { ColorAnimation { duration: 100 } }
    }
    contentItem: Item {
        implicitWidth: contents.implicitWidth
        implicitHeight: contents.implicitHeight
        Row {
            id: contents
            spacing: 7
            anchors.centerIn: parent
            Icon {
                name: control.iconName
                visible: name.length > 0
                width: 16; height: 16
                anchors.verticalCenter: parent.verticalCenter
                tint: control.tone === "primary" ? "#ffffff" : control.tone === "danger" ? "#a64e50" : "#63746a"
            }
            Text {
                anchors.verticalCenter: parent.verticalCenter
                visible: text.length > 0
                text: control.text
                font.pixelSize: 13
                font.weight: control.tone === "primary" ? Font.DemiBold : Font.Normal
                color: control.tone === "primary" ? "#ffffff" : control.tone === "danger" ? "#a64e50" : "#344b3b"
            }
        }
    }
    ToolTip.visible: hovered && hint.length > 0
    ToolTip.delay: 600
    ToolTip.text: hint
}
