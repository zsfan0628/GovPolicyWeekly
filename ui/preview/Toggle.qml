import QtQuick
import QtQuick.Controls

AbstractButton {
    id: control
    implicitWidth: 34
    implicitHeight: 22
    checkable: true
    hoverEnabled: true
    background: Rectangle {
        x: 0; y: 2; width: 34; height: 18
        radius: 9
        color: control.checked ? "#448b65" : "#cdd7cf"
        border.width: control.activeFocus ? 1 : 0
        border.color: "#ffffff"
        Behavior on color { ColorAnimation { duration: 140 } }
        Rectangle {
            x: control.checked ? 18 : 3
            y: 3; width: 12; height: 12; radius: 6
            color: "#ffffff"
            Behavior on x { NumberAnimation { duration: 140; easing.type: Easing.OutCubic } }
        }
    }
}
