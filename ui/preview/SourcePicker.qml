import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: control
    property alias opened: selector.visible
    property var glassTexture: null
    property Item glassScene: null
    property bool reducedTransparency: false
    implicitHeight: 40
    implicitWidth: 480
    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: "选择采集站点"
    function toggle() { selector.visible ? selector.close() : selector.open() }
    Keys.onSpacePressed: toggle()
    Keys.onReturnPressed: toggle()
    Rectangle {
        anchors.fill: parent; color: "#ffffff"; radius: 6; border.width: 1
        border.color: selector.visible || control.activeFocus ? "#4f8f6b" : trigger.containsMouse ? "#9caea1" : "#d6dfd8"
        Icon { x: 12; anchors.verticalCenter: parent.verticalCenter; name: "globe"; width: 17; height: 17 }
        Text {
            x: 40; anchors.verticalCenter: parent.verticalCenter; font.pixelSize: 13; color: "#26322b"
            text: sources.selectedCount === sources.total ? "全部站点" : sources.selectedCount === 0 ? "未选择站点" : "自定义站点"
        }
        Text { anchors.right: arrow.left; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter; text: sources.selectedCount + " / " + sources.total; color: "#636763"; font.pixelSize: 12 }
        Icon {
            id: arrow; anchors.right: parent.right; anchors.rightMargin: 12; anchors.verticalCenter: parent.verticalCenter
            name: "chevron-down"; width: 14; height: 14; rotation: selector.visible ? 180 : 0
            Behavior on rotation { NumberAnimation { duration: 140 } }
        }
        MouseArea { id: trigger; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: { control.forceActiveFocus(); control.toggle() } }
    }
    Popup {
        id: selector
        objectName: "sourcePopup"
        y: control.height + 7
        width: Math.max(440, control.width); height: 434
        padding: 0
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutsideParent
        onAboutToShow: {
            selector.height = Math.min(434, Overlay.overlay.height - 24)
            let position = control.mapToItem(Overlay.overlay, 0, 0)
            selector.y = position.y + control.height + selector.height + 7 > Overlay.overlay.height - 12
                       ? -selector.height - 7 : control.height + 7
        }
        onOpened: { sourceSearch.forceActiveFocus() }
        background: GlassSurface { texture: control.glassTexture; scene: control.glassScene; radius: 16; frost: 10; whiteMix: 0.94; reducedTransparency: control.reducedTransparency }
        enter: Transition { NumberAnimation { property: "opacity"; from: 0; to: 1; duration: 150 } }
        exit: Transition { NumberAnimation { property: "opacity"; to: 0; duration: 100 } }
        contentItem: ColumnLayout {
            spacing: 0
            Item {
                Layout.fillWidth: true; Layout.preferredHeight: 54
                Icon { x: 17; anchors.verticalCenter: parent.verticalCenter; name: "search"; width: 17; height: 17 }
                TextField {
                    id: sourceSearch; objectName: "sourceSearch"
                    anchors { left: parent.left; leftMargin: 43; right: parent.right; rightMargin: 14; verticalCenter: parent.verticalCenter }
                    height: 38; padding: 0; color: "#262726"; font.pixelSize: 13; placeholderText: "搜索站点、地区或部门"; placeholderTextColor: "#707470"
                    background: Item {}
                    onTextChanged: sourceFilter.query = text
                }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#e5ece5" }
            RowLayout {
                Layout.fillWidth: true; Layout.leftMargin: 16; Layout.rightMargin: 16; Layout.preferredHeight: 44
                CheckControl {
                    objectName: "allSourcesCheck"; text: "全部站点"
                    checked: sources.selectedCount === sources.total
                    partial: sources.selectedCount > 0 && sources.selectedCount < sources.total
                    onClicked: sources.selectAll(sources.selectedCount !== sources.total)
                }
                Item { Layout.fillWidth: true }
                Text { text: "已选 " + sources.selectedCount + " 个"; color: "#5a5d5a"; font.pixelSize: 12 }
                AppButton { text: "清空"; compact: true; tone: "ghost"; onClicked: sources.selectAll(false) }
            }
            ListView {
                id: list; objectName: "sourcePopupList"
                Layout.fillWidth: true; Layout.fillHeight: true
                clip: true; model: sourceFilter
                boundsBehavior: Flickable.StopAtBounds
                ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded; width: 8 }
                section.property: "region"
                section.delegate: Item {
                    required property string section
                    width: list.width; height: 31
                    Text { x: 16; anchors.verticalCenter: parent.verticalCenter; text: section === "国家" ? "国家部委" : section; color: "#6a6d6a"; font.pixelSize: 11; font.weight: Font.DemiBold }
                }
                delegate: Item {
                    required property int siteId
                    required property string siteName
                    required property bool selected
                    width: list.width; height: 37
                    Rectangle { anchors.fill: parent; anchors.leftMargin: 6; anchors.rightMargin: 6; radius: 5; color: rowMouse.containsMouse ? "#e6ede6" : "transparent" }
                    Rectangle {
                        x: 17; y: 11; width: 15; height: 15; radius: 4; border.width: 1
                        color: selected ? "#39835d" : "transparent"; border.color: selected ? "#39835d" : "#a5b0a8"
                        Icon { anchors.centerIn: parent; width: 11; height: 11; name: "check"; visible: selected; tint: "#ffffff" }
                    }
                    Text { x: 43; anchors.verticalCenter: parent.verticalCenter; width: parent.width - 63; text: siteName; color: "#333533"; font.pixelSize: 13; elide: Text.ElideRight }
                    MouseArea { id: rowMouse; objectName: "siteRow" + parent.siteId; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: sources.toggle(parent.siteId) }
                }
                Text { anchors.centerIn: parent; text: "没有匹配的站点"; color: "#68776c"; font.pixelSize: 13; visible: list.count === 0 }
            }
            Rectangle { Layout.fillWidth: true; height: 1; color: "#e5ece5" }
            RowLayout {
                Layout.fillWidth: true; Layout.preferredHeight: 40; Layout.leftMargin: 16; Layout.rightMargin: 12
                Text { text: "国家部委 / 江苏 / 湖北 / 黑龙江 / 南通"; color: "#6d706d"; font.pixelSize: 11; Layout.fillWidth: true }
                AppButton { text: "完成"; compact: true; tone: "ghost"; onClicked: selector.close() }
            }
        }
    }
}
