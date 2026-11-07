import QtQuick

Item {
    id: row
    objectName: "logRow"
    required property string logTime
    required property string level
    required property string message
    readonly property real timeBaseline: timestamp.y + timestamp.baselineOffset
    readonly property real levelBaseline: severity.y + severity.baselineOffset
    readonly property real messageBaseline: content.y + content.baselineOffset
    readonly property real messageColumn: content.x
    readonly property rect messageInk: messageMetrics.tightBoundingRect(message.replace(/\n/g, ""))
    readonly property rect timeInk: timeMetrics.tightBoundingRect(logTime)
    readonly property rect levelInk: levelMetrics.tightBoundingRect(level)
    readonly property real inkTop: Math.min(messageInk.y, timeInk.y, levelInk.y)
    readonly property real inkBottom: Math.max(
        messageInk.y + messageInk.height + Math.max(0, content.lineCount - 1) * content.lineHeight,
        timeInk.y + timeInk.height, levelInk.y + levelInk.height)
    readonly property real inkHeight: Math.max(1, inkBottom - inkTop)
    readonly property real topInset: content.y + content.baselineOffset + inkTop
    readonly property real bottomInset: height - 1 - (content.y + content.baselineOffset + inkBottom)
    readonly property string severityColor: level === "ERROR" ? "#b44747"
        : level === "WARN" || level === "STOP" ? "#98652f"
        : level === "READY" || level === "DONE" ? "#267451" : "#65717c"
    // Center the visible glyph area, including fallback CJK fonts, above the divider.
    height: Math.ceil(Math.max(27, inkHeight + 12)) + 1
    FontMetrics { id: messageMetrics; font: content.font }
    FontMetrics { id: timeMetrics; font: timestamp.font }
    FontMetrics { id: levelMetrics; font: severity.font }
    Rectangle { anchors.fill: parent; color: hovered.hovered ? "#edf2f5" : "transparent" }
    HoverHandler { id: hovered }
    Text {
        id: timestamp; objectName: "logTimestamp"
        x: 0; width: 70
        anchors.baseline: content.baseline
        text: row.logTime; textFormat: Text.PlainText
        font.family: Qt.platform.os === "windows" ? "Consolas" : "Menlo"
        font.pixelSize: 11; color: "#7b8792"
        elide: Text.ElideRight
    }
    Text {
        id: severity; objectName: "logSeverity"
        x: 82; width: 56
        anchors.baseline: content.baseline
        text: row.level; textFormat: Text.PlainText
        font.family: Qt.platform.os === "windows" ? "Consolas" : "Menlo"
        font.pixelSize: 11; color: row.severityColor
        elide: Text.ElideRight
    }
    Text {
        id: content; objectName: "logMessage"
        x: 150; width: Math.max(1, row.width - x - 8)
        y: (row.height - 1 - row.inkHeight) / 2 - row.inkTop - baselineOffset
        text: row.message; textFormat: Text.PlainText
        font.pixelSize: 11; color: row.level === "ERROR" ? "#a33c3c" : "#3f4b56"
        wrapMode: Text.WrapAnywhere
        lineHeightMode: Text.FixedHeight; lineHeight: 17
    }
    Rectangle { anchors.bottom: parent.bottom; width: parent.width; height: 1; color: "#f0f3f5" }
}
