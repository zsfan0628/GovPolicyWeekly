import "Pearl.js" as Pearl
import QtQuick
import QtQuick.Controls

TabButton {
    id: control
    implicitHeight: 30
    padding: 0
    topInset: 0; bottomInset: 0; leftInset: 0; rightInset: 0
    background: Rectangle {
        radius: 5
        color: control.checked ? "#ffffff" : control.hovered ? Pearl.soft : "transparent"
        border.width: control.checked || control.visualFocus ? 1 : 0
        border.color: control.visualFocus ? Pearl.accent : Pearl.line
    }
    contentItem: Text {
        text: control.text; font.pixelSize: 12; color: Pearl.active
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
}
