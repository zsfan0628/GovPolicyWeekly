import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Pearl.js" as Pearl

AbstractButton {
    id: control
    required property string label
    required property string symbol
    property string summary
    property color fill: Pearl.soft
    property bool expanded: false
    Layout.fillWidth: true
    implicitHeight: 48
    hoverEnabled: true
    Accessible.name: label + "：" + summary
    Accessible.checkable: true
    Accessible.checked: expanded
    background: Rectangle { color: control.fill; radius: 7; border.width:control.visualFocus || control.expanded || control.hovered ? 1 : 0; border.color:control.visualFocus ? Pearl.accent : Pearl.frame }
    contentItem: RowLayout {
        spacing:10
        Icon { Layout.leftMargin:12; name:control.symbol; tint:Pearl.muted; width:17; height:17 }
        Text { text:control.label; color:Pearl.ink; font.pixelSize:15; font.weight:Font.DemiBold }
        Text { text:control.summary; color:Pearl.muted; font.pixelSize:12; Layout.fillWidth:true; Layout.minimumWidth:0; horizontalAlignment:Text.AlignRight; elide:Text.ElideRight }
        Icon { name:"chevron-down"; width:14; height:14; Layout.rightMargin:12; rotation:control.expanded?180:0; tint:Pearl.muted }
    }
}
