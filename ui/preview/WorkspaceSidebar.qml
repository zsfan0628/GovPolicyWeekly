import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: sidebar
    property int currentIndex: 0
    property int selectedCount: 0
    property int totalCount: 0
    property bool running: false
    signal chosen(int index)
    signal replayRequested()
    color: "#f3f6f8"
    Rectangle { anchors.right: parent.right; width: 1; height: parent.height; color: "#dce4e9" }
    ColumnLayout {
        anchors { fill: parent; leftMargin: 14; rightMargin: 14; topMargin: 24; bottomMargin: 20 }
        spacing: 6
        RowLayout {
            Layout.fillWidth: true; Layout.bottomMargin: 22; spacing: 9
            Icon { name: "file-text"; width: 25; height: 25; tint: "#285b79" }
            Column {
                spacing: 3
                Text { text: "政策周报"; font.pixelSize: 17; font.weight: Font.DemiBold; color: "#253b4b" }
                Text { text: "POLICY WEEKLY"; font.pixelSize: 9; color: "#7b8c98" }
            }
        }
        Text { text: "工作空间"; color: "#8997a2"; font.pixelSize: 10; Layout.leftMargin: 10; Layout.bottomMargin: 6 }
        Repeater {
            model: ["采集任务", "站点管理", "历史报告", "偏好设置"]
            delegate: Button {
                id: nav
                required property int index
                required property string modelData
                objectName: "nav" + index
                Layout.fillWidth: true; Layout.preferredHeight: 40
                hoverEnabled: true
                Accessible.name: modelData
                Accessible.role: Accessible.PageTab
                Accessible.selected: sidebar.currentIndex === index
                onClicked: sidebar.chosen(index)
                background: Rectangle {
                    radius: 6
                    color: sidebar.currentIndex === nav.index ? "#e1ebf3" : nav.hovered ? "#eaf0f4" : "transparent"
                    Rectangle { x: 0; anchors.verticalCenter: parent.verticalCenter; width: 3; height: 18; radius: 1; color: "#3479ad"; visible: sidebar.currentIndex === nav.index }
                    border.width: nav.activeFocus ? 1 : 0; border.color: "#3479ad"
                }
                contentItem: RowLayout {
                    spacing: 10
                    Icon { Layout.leftMargin: 11; name: ["layout-dashboard", "globe", "history", "settings-2"][nav.index]; width: 17; height: 17; tint: sidebar.currentIndex === nav.index ? "#28668f" : "#74838e" }
                    Text { text: nav.modelData; Layout.fillWidth: true; font.pixelSize: 13; font.weight: sidebar.currentIndex === nav.index ? Font.Medium : Font.Normal; color: sidebar.currentIndex === nav.index ? "#214f70" : "#536573" }
                }
            }
        }
        Rectangle { Layout.fillWidth: true; Layout.topMargin: 16; Layout.bottomMargin: 9; height: 1; color: "#e0e7ec" }
        RowLayout {
            Layout.fillWidth: true; Layout.leftMargin: 10; Layout.rightMargin: 10
            Text { text: "站点范围"; font.pixelSize: 11; color: "#7c8d98"; Layout.fillWidth: true }
            Text { text: sidebar.selectedCount + " / " + sidebar.totalCount; font.pixelSize: 11; color: "#435c6d" }
        }
        Item { Layout.fillHeight: true }
        Item {
            Layout.fillWidth: true; Layout.preferredHeight: 146; clip: true
            Image { anchors.fill: parent; source: "assets/glacier-spiti.jpg"; fillMode: Image.PreserveAspectCrop; smooth: true }
        }
        RowLayout {
            Layout.topMargin: 10; Layout.fillWidth: true; spacing: 6
            Rectangle { width: 5; height: 5; radius: 2.5; color: sidebar.running ? "#388169" : "#8da19d" }
            Text { text: sidebar.running ? "任务运行中" : "本地工作台"; color: "#6b7f8e"; font.pixelSize: 10; Layout.fillWidth: true }
            AppButton { iconName: "rotate-ccw"; hint: "重播启动动画"; compact: true; tone: "ghost"; onClicked: sidebar.replayRequested() }
        }
    }
}
