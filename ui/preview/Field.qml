import "Pearl.js" as Pearl
import QtQuick
import QtQuick.Controls

TextField {
    id: control
    implicitHeight: 38
    leftPadding: 12; rightPadding: 12
    color: Pearl.ink
    placeholderTextColor: Pearl.frame
    selectionColor: Pearl.line
    selectedTextColor: Pearl.ink
    font.pixelSize: 13
    selectByMouse: true
    background: Rectangle {
        color: "#ffffff"
        radius: 6
        border.width: 1
        border.color: control.activeFocus ? Pearl.accent : control.hovered ? Pearl.frame : Pearl.line
        Behavior on border.color { ColorAnimation { duration: 120 } }
    }
}
