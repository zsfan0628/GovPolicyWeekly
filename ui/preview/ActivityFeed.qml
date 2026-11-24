import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "Pearl.js" as Pearl

Item {
    id: feed
    signal actionRequested(string action)
    ListView {
        id: stream; objectName:"activityList"
        anchors.fill:parent; model:preview.activityModel; clip:true
        property bool followLatest:true
        boundsBehavior:Flickable.StopAtBounds
        function tail() { if (followLatest && count) positionViewAtEnd() }
        onCountChanged: { if (!count) followLatest=true; if (followLatest) Qt.callLater(tail) }
        onMovementStarted:followLatest=false
        onMovementEnded:followLatest=atYEnd
        WheelHandler {
            target:null; blocking:false
            onWheel:function(e) {
                if (e.angleDelta.y>0 || e.pixelDelta.y>0) stream.followLatest=false
                else Qt.callLater(function(){ if(stream.atYEnd) stream.followLatest=true })
            }
        }
        ScrollBar.vertical:ScrollBar {
            width:7
            onPressedChanged:stream.followLatest=!pressed && stream.atYEnd
        }
        delegate:Item {
            id:entry
            required property int index
            required property string eventKind
            required property string eventTitle
            required property string eventDetail
            required property string eventTime
            required property string eventAction
            readonly property bool attention:eventKind==="warning" || eventKind==="failed"
            readonly property color mark:attention ? "#875027" : Pearl.accent
            width:stream.width-12; height:Math.max(48,copy.implicitHeight+10)
            Rectangle { x:12; y:30; width:1; height:parent.height-24; visible:entry.index<stream.count-1; color:Pearl.line }
            Rectangle {
                x:0; y:7; width:25; height:25; radius:13; color:entry.attention ? "#f7ecdf" : Pearl.soft
                Icon { anchors.centerIn:parent; width:14; height:14; tint:entry.mark
                    name:entry.eventAction==="report" ? "file-text" : entry.eventKind==="started" ? "play" :
                         entry.eventKind==="paused" ? "square" : entry.eventKind==="working" ? "globe" :
                         entry.attention ? "activity" : "check" }
            }
            Column {
                id:copy; x:38; y:5; width:Math.max(1,action.x-x-12); spacing:2
                Text { width:parent.width; text:entry.eventTitle; textFormat:Text.PlainText; wrapMode:Text.WrapAnywhere
                    font.pixelSize:14; font.weight:Font.Medium; color:entry.attention ? entry.mark : Pearl.ink }
                Text { width:parent.width; visible:text.length>0; text:entry.eventDetail; textFormat:Text.PlainText
                    wrapMode:Text.WrapAnywhere; font.pixelSize:12; color:Pearl.muted }
            }
            AppButton {
                id:action; anchors.right:stamp.left; anchors.rightMargin:12; anchors.verticalCenter:parent.verticalCenter
                visible:entry.eventAction!==""; width:visible ? implicitWidth : 0; compact:true; tone:"ghost"
                text:entry.eventAction==="report" ? "打开 PDF" : entry.eventAction==="coverage" ? "查看详情" : "技术明细"
                iconName:entry.eventAction==="report" ? "external-link" : "chevron-right"
                onClicked:feed.actionRequested(entry.eventAction)
            }
            Text { id:stamp; anchors.right:parent.right; y:8; text:entry.eventTime; font.pixelSize:11; color:Pearl.muted }
        }
    }
    RowLayout {
        visible:stream.count===0; anchors.left:parent.left; anchors.top:parent.top; anchors.topMargin:10; spacing:12
        Icon { name:"calendar-days"; width:22; height:22; tint:Pearl.accent }
        Column {
            spacing:3
            Text { text:"暂无本次任务动态"; font.pixelSize:14; font.weight:Font.Medium; color:Pearl.ink }
            Text { text:"当前已选择 "+sources.selectedCount+" 个采集站点"; font.pixelSize:12; color:Pearl.muted }
        }
    }
    AppButton { anchors.right:parent.right; anchors.bottom:parent.bottom; visible:!stream.followLatest && !stream.atYEnd
        iconName:"arrow-down"; compact:true; hint:"回到最新动态"; onClicked:{ stream.followLatest=true; stream.tail() } }
}
