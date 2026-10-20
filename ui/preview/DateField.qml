import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: control
    property string value: "2026-10-12"
    property alias opened: calendar.visible
    property int viewYear: new Date().getFullYear()
    property int viewMonth: new Date().getMonth()
    property var glassTexture: null
    property Item glassScene: null
    property bool reducedTransparency: false
    implicitWidth: 210
    implicitHeight: 38
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: "选择日期 " + value
    function toggle() { calendar.visible ? calendar.close() : calendar.open() }
    function shiftMonth(amount) {
        let d = new Date(viewYear, viewMonth + amount, 1)
        viewYear = d.getFullYear(); viewMonth = d.getMonth()
    }
    function cellDate(index) {
        let offset = (new Date(viewYear, viewMonth, 1).getDay() + 6) % 7
        return new Date(viewYear, viewMonth, index - offset + 1)
    }
    function format(d) {
        return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0")
    }
    Keys.onSpacePressed: toggle()
    Keys.onReturnPressed: toggle()
    Rectangle {
        anchors.fill: parent
        radius: 6; color: "#ffffff"
        border.width: 1
        border.color: calendar.visible || control.activeFocus ? "#4f8f6b" : trigger.containsMouse ? "#9caea1" : "#d6dfd8"
        Icon { x: 11; anchors.verticalCenter: parent.verticalCenter; name: "calendar-days"; width: 16; height: 16 }
        Text { x: 37; anchors.verticalCenter: parent.verticalCenter; text: control.value; color: "#26322b"; font.pixelSize: 13 }
        Icon {
            anchors.right: parent.right; anchors.rightMargin: 10; anchors.verticalCenter: parent.verticalCenter
            name: "chevron-down"; width: 14; height: 14
            rotation: calendar.visible ? 180 : 0
            Behavior on rotation { NumberAnimation { duration: 140 } }
        }
        MouseArea {
            id: trigger; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
            onClicked: { control.forceActiveFocus(); control.toggle() }
        }
    }
    Popup {
        id: calendar
        objectName: control.objectName + "Popup"
        x: 0; y: control.height + 7
        width: 288; height: 300
        padding: 15
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        onOpened: {
            let parts = control.value.split("-")
            control.viewYear = Number(parts[0]); control.viewMonth = Number(parts[1]) - 1
        }
        background: GlassSurface {
            texture: control.glassTexture; scene: control.glassScene
            radius: 16; frost: 10; whiteMix: 0.92
            reducedTransparency: control.reducedTransparency
        }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 140 } }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 100 } }
        contentItem: ColumnLayout {
            spacing: 7
            RowLayout {
                Layout.fillWidth: true
                Text { text: control.viewYear + " 年 " + (control.viewMonth + 1) + " 月"; color: "#272827"; font.pixelSize: 14; Layout.fillWidth: true }
                AppButton { objectName: control.objectName + "Previous"; iconName: "chevron-left"; compact: true; tone: "ghost"; hint: "上个月"; onClicked: control.shiftMonth(-1) }
                AppButton { objectName: control.objectName + "Next"; iconName: "chevron-right"; compact: true; tone: "ghost"; hint: "下个月"; onClicked: control.shiftMonth(1) }
            }
            GridLayout {
                columns: 7; rowSpacing: 2; columnSpacing: 0
                Layout.fillWidth: true
                Repeater {
                    model: ["一", "二", "三", "四", "五", "六", "日"]
                    Text { required property string modelData; text: modelData; color: "#7a7d7a"; font.pixelSize: 11; horizontalAlignment: Text.AlignHCenter; Layout.fillWidth: true; Layout.preferredHeight: 23 }
                }
                Repeater {
                    model: 42
                    delegate: Item {
                        required property int index
                        objectName: control.objectName + "Day" + index
                        property date day: control.cellDate(index)
                        property bool selected: control.format(day) === control.value
                        Layout.fillWidth: true; Layout.preferredHeight: 28
                        Rectangle {
                            anchors.centerIn: parent; width: 29; height: 27; radius: 5
                            color: parent.selected ? "#267451" : dayMouse.containsMouse ? "#e4ebe4" : "transparent"
                            border.width: !parent.selected && control.format(parent.day) === control.format(new Date()) ? 1 : 0
                            border.color: "#7a7e7a"
                        }
                        Text {
                            anchors.centerIn: parent; text: parent.day.getDate(); font.pixelSize: 12
                            color: parent.selected ? "#ffffff" : parent.day.getMonth() === control.viewMonth ? "#26322b" : "#a2aca5"
                        }
                        MouseArea {
                            id: dayMouse; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor
                            onClicked: { control.value = control.format(parent.day); calendar.close() }
                        }
                    }
                }
            }
            Item { Layout.fillHeight: true }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#e5ece5" }
            AppButton { text: "今天"; tone: "ghost"; compact: true; Layout.alignment: Qt.AlignHCenter; onClicked: { control.value = control.format(new Date()); calendar.close() } }
        }
    }
}
