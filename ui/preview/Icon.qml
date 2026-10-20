import QtQuick

Item {
    property string name: "file-text"
    property color tint: "#728477"
    implicitWidth: 18
    implicitHeight: 18
    width: 18
    height: 18
    Image {
        anchors.fill: parent
        source: "image://icons/" + parent.name + "/" + parent.tint.toString().substring(1)
        sourceSize.width: 64
        sourceSize.height: 64
        fillMode: Image.PreserveAspectFit
        smooth: true
    }
    Accessible.ignored: true
}
