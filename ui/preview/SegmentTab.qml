import QtQuick
import QtQuick.Controls

TabButton {
    id: control
    implicitHeight: 30
    padding: 0
    topInset: 0; bottomInset: 0; leftInset: 0; rightInset: 0
    background: Rectangle {
        radius: 5
        color: control.checked ? "#ffffff" : control.hovered ? "#f0f5f1" : "transparent"
        border.width: control.checked || control.activeFocus ? 1 : 0
        border.color: control.activeFocus ? "#6194c2" : "#c9ddd0"
    }
    contentItem: Text {
        text: control.text; font.pixelSize: 12; color: "#385a49"
        horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
    }
}
