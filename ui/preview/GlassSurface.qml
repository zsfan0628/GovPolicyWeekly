import QtQuick

Item {
    id: glass
    property var texture: null
    property Item scene: null
    property real radius: 24
    property real frost: 4
    property real thickness: 12
    property real whiteMix: 0.55
    property bool reducedTransparency: false
    property point light: Qt.point(0.15, 0.1)
    readonly property bool shaderFailed: material.status === ShaderEffect.Error
    readonly property string renderLog: material.log
    readonly property point scenePoint: {
        let geometry = x + y + width + height + (scene ? scene.width + scene.height : 0)
        return scene && geometry >= 0 ? mapToItem(scene, 0, 0) : Qt.point(0, 0)
    }
    Rectangle {
        anchors.fill: parent; anchors.topMargin: 4; anchors.bottomMargin: -4
        radius: glass.radius
        color: "#0c172b20"
    }
    Rectangle {
        anchors.fill: parent; radius: glass.radius
        color: "#f3f7f4"
        visible: glass.reducedTransparency || !glass.texture
        border.width: 1; border.color: "#ffffff"
    }
    ShaderEffect {
        id: material
        objectName: "glassShader"
        anchors.fill: parent
        visible: !glass.reducedTransparency && glass.texture !== null
        property var backdrop: glass.texture
        property vector2d surfaceSize: Qt.vector2d(width, height)
        property vector2d sceneSize: Qt.vector2d(glass.scene ? glass.scene.width : 1, glass.scene ? glass.scene.height : 1)
        property vector2d scenePosition: Qt.vector2d(glass.scenePoint.x, glass.scenePoint.y)
        property vector2d lightPosition: Qt.vector2d(glass.light.x, glass.light.y)
        property real cornerRadius: glass.radius
        property real frost: glass.frost
        property real thickness: glass.thickness
        property real whiteMix: glass.whiteMix
        fragmentShader: "shaders/glass.frag.qsb"
    }
}
