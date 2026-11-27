import "Pearl.js" as Pearl
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
    topInset: 0; bottomInset: 0; leftInset: 0; rightInset: 0
    hoverEnabled: true
    opacity: enabled ? 1 : 0.38
    Accessible.name: text || hint
    background: Rectangle {
        radius: 6
        color: control.tone === "primary" ? (control.down ? Pearl.active : control.hovered ? Pearl.active : Pearl.accent)
             : control.tone === "danger" ? (control.hovered ? "#f6dddd" : "#f9ecec")
             : control.tone === "ghost" ? (control.hovered ? "#140d3421" : "transparent")
             : control.hovered ? Pearl.soft : "#ffffff"
        border.width: control.visualFocus || control.tone === "default" ? 1 : 0
        border.color: control.visualFocus ? Pearl.accent : Pearl.line
        Behavior on color { ColorAnimation { duration: 100 } }
    }
    contentItem: Item {
        implicitWidth: contents.implicitWidth
        implicitHeight: contents.implicitHeight
        Row {
            id: contents
            objectName: "buttonContents"
            spacing: 7
            height: Math.max(buttonIcon.visible ? buttonIcon.height : 0, buttonLabel.visible ? buttonLabel.implicitHeight : 0)
            anchors.centerIn: parent
            Icon {
                id: buttonIcon; objectName: "buttonIcon"
                name: control.iconName
                visible: name.length > 0
                width: 16; height: 16
                anchors.verticalCenter: parent.verticalCenter
                tint: control.tone === "primary" ? "#ffffff" : control.tone === "danger" ? "#a64e50" : Pearl.muted
            }
            Text {
                id: buttonLabel; objectName: "buttonLabel"
                anchors.verticalCenter: parent.verticalCenter
                visible: text.length > 0
                text: control.text
                font.pixelSize: 13
                font.weight: control.tone === "primary" ? Font.DemiBold : Font.Normal
                color: control.tone === "primary" ? "#ffffff" : control.tone === "danger" ? "#a64e50" : Pearl.ink
            }
        }
    }
    ToolTip.visible: hovered && hint.length > 0
    ToolTip.delay: 600
    ToolTip.text: hint
}
