import QtQuick
import QtQuick.Controls

TextField {
    id: control
    implicitHeight: 38
    leftPadding: 12; rightPadding: 12
    color: "#26342b"
    placeholderTextColor: "#94a197"
    selectionColor: "#c1ddcc"
    selectedTextColor: "#20372a"
    font.pixelSize: 13
    selectByMouse: true
    background: Rectangle {
        color: "#ffffff"
        radius: 6
        border.width: 1
        border.color: control.activeFocus ? "#5c9780" : control.hovered ? "#a4b7a9" : "#d9e2dc"
        Behavior on border.color { ColorAnimation { duration: 120 } }
    }
}
