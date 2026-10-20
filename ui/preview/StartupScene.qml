import QtQuick
import QtQuick.Controls

Item {
    id: startup
    property real progress: 0
    property real departure: 0
    property bool reducedMotion: false
    signal skipRequested()
    Rectangle { anchors.fill: parent; color: "#0c1411"; opacity: 1 - startup.departure }
    Canvas {
        id: particles
        anchors.fill: parent
        renderTarget: Canvas.Image
        opacity: 1 - startup.departure
        property real frame: startup.progress
        readonly property var points: JSON.parse(preview.introPointsJson)
        property real mouseX: -1000
        property real mouseY: -1000
        onFrameChanged: requestPaint()
        onMouseXChanged: requestPaint()
        onMouseYChanged: requestPaint()
        onPaint: {
            let ctx = getContext("2d")
            ctx.clearRect(0, 0, width, height)
            let textWidth = Math.min(460, width * 0.48)
            for (let i = 0; i < points.length; ++i) {
                let point = points[i]
                let seed = (i * 0.61803398875) % 1
                let p = Math.max(0, Math.min(1, (frame - seed * 0.14) / 0.86))
                let ease = 1 - Math.pow(1 - p, 4)
                let angle = seed * 6.283185 + (1 - p) * (3.0 + point.y * 2.4)
                let distance = (0.2 + ((i * 0.371) % 1) * 0.65) * width
                let homeX = width * 0.5 + (point.x - 0.5) * textWidth
                let homeY = height * 0.46 + (point.y - 0.5) * textWidth * 0.26
                let x = homeX + Math.cos(angle) * distance * (1 - ease)
                let y = homeY + Math.sin(angle) * distance * (1 - ease) * 0.7
                let dx = x - mouseX, dy = y - mouseY
                let repel = Math.max(0, 1 - Math.sqrt(dx * dx + dy * dy) / 100) * 12 * (1 - frame)
                x += dx / (Math.abs(dx) + 1) * repel; y += dy / (Math.abs(dy) + 1) * repel
                let size = 1.1 + ease * 0.85
                ctx.globalAlpha = (0.16 + ease * 0.84) * Math.min(1, frame * 8)
                ctx.fillStyle = i % 5 === 0 ? "#90d4c2" : i % 7 === 0 ? "#b4d3df" : "#e7f0eb"
                ctx.fillRect(x, y, size, size)
            }
            ctx.globalAlpha = 1
        }
    }
    MouseArea {
        anchors.fill: parent; hoverEnabled: true; acceptedButtons: Qt.NoButton
        onPositionChanged: function(mouse) { particles.mouseX = mouse.x; particles.mouseY = mouse.y }
    }
    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height * 0.46 + Math.min(460, parent.width * 0.48) * 0.26 * 0.5 + 26
        spacing: 16
        opacity: Math.max(0, (startup.progress - 0.58) / 0.42) * (1 - startup.departure)
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "POLICY WEEKLY"; color: "#a0b8ad"; font.pixelSize: 13 }
    }
    AppButton {
        objectName: "skipIntro"
        anchors.right: parent.right; anchors.rightMargin: 28; anchors.bottom: parent.bottom; anchors.bottomMargin: 24
        text: "跳过"; tone: "ghost"; compact: true
        onClicked: startup.skipRequested()
    }
    Rectangle {
        x: 0; y: parent.height - 2; height: 2
        width: parent.width * startup.progress
        color: "#739e87"; opacity: 1 - startup.departure
    }
    Keys.onEscapePressed: skipRequested()
}
