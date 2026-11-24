import "Pearl.js" as Pearl
import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control
    property bool partial: false
    implicitHeight: 30
    implicitWidth: label.implicitWidth + 28
    checkable: true
    padding: 0
    topInset: 0; bottomInset: 0; leftInset: 0; rightInset: 0
    hoverEnabled: true
    contentItem: Item {
        Rectangle {
            x: 0; anchors.verticalCenter: parent.verticalCenter
            width: 16; height: 16; radius: 4
            color: control.checked || control.partial ? Pearl.accent : Pearl.soft
            border.width: 1
            border.color: control.checked || control.partial ? Pearl.accent : control.activeFocus ? Pearl.accent : Pearl.muted
            Icon {
                anchors.centerIn: parent
                width: 12; height: 12
                name: control.partial ? "minus" : "check"
                tint: "#ffffff"
                visible: control.checked || control.partial
            }
        }
        Text {
            id: label
            x: 26; anchors.verticalCenter: parent.verticalCenter
            text: control.text
            font.pixelSize: 13
            color: Pearl.ink
        }
    }
}
