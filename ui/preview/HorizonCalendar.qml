import QtQuick
import "Pearl.js" as Pearl

Item {
    id: period
    required property string start
    required property string end
    readonly property real first:Date.parse(start+"T00:00:00Z")
    readonly property real last:Date.parse(end+"T00:00:00Z")
    readonly property real days:(last-first)/86400000+1
    readonly property bool valid:isFinite(days) && days>0
    function monthOf(iso) { return Number(iso.slice(0,4))*12+Number(iso.slice(5,7))-1 }
    property int offset:0
    onStartChanged:offset=0
    onEndChanged:offset=0
    readonly property int month:valid ? monthOf(start)+offset : 0
    readonly property int year:Math.floor(month/12)
    readonly property int monthIndex:month%12
    readonly property real monthStart:Date.UTC(year,monthIndex,1)
    readonly property int leading:(new Date(monthStart).getUTCDay()+6)%7
    readonly property int lastDay:new Date(Date.UTC(year,monthIndex+1,0)).getUTCDate()
    readonly property int lastOffset:valid ? monthOf(end)-monthOf(start) : 0
    Accessible.role:Accessible.Grouping
    Accessible.name:valid ? "统计周期："+start+" 至 "+end+"，共 "+days+" 天" : "请选择有效的统计周期"

    Item {
        id:countBlock
        anchors.left:parent.left; anchors.verticalCenter:parent.verticalCenter
        width:Math.min(138,parent.width*.31); height:80
        Text { id:label; text:"统计天数"; font.pixelSize:13; color:Pearl.muted }
        Row {
            anchors.top:label.bottom; anchors.topMargin:3; spacing:5
            Text {
                id:count; objectName:"calendarDayCount"
                width:Math.min(implicitWidth,countBlock.width-23); height:55
                text:period.valid ? String(period.days) : "待选"; color:Pearl.active
                font.family:workspaceFonts.serif; font.pixelSize:period.valid ? 46 : 24
                fontSizeMode:Text.Fit; minimumPixelSize:14; verticalAlignment:Text.AlignVCenter
            }
            Text { visible:period.valid; text:"天"; font.pixelSize:14; color:Pearl.muted; anchors.baseline:count.baseline }
        }
    }

    Item {
        id:sheet
        visible:period.valid; anchors.left:countBlock.right; anchors.leftMargin:14
        anchors.right:parent.right; anchors.verticalCenter:parent.verticalCenter
        height:Math.min(182,parent.height)
        Text {
            objectName:"rangeMonthLabel"; text:period.year+" 年 "+(period.monthIndex+1)+" 月"
            anchors.left:parent.left; anchors.leftMargin:5; y:3
            font.pixelSize:14; font.weight:Font.DemiBold; color:Pearl.ink
        }
        Row {
            visible:period.lastOffset>0; anchors.right:parent.right
            AppButton { objectName:"rangePrev"; iconName:"chevron-left"; tone:"ghost"; hint:"上一个月"
                width:26; height:24; enabled:period.offset>0; onClicked:period.offset-- }
            AppButton { objectName:"rangeNext"; iconName:"chevron-right"; tone:"ghost"; hint:"下一个月"
                width:26; height:24; enabled:period.offset<period.lastOffset; onClicked:period.offset++ }
        }
        readonly property real colWidth:width/7
        readonly property real rowHeight:(height-46)/6
        Repeater {
            model:["一","二","三","四","五","六","日"]
            Text { required property int index; required property string modelData
                x:index*sheet.colWidth; y:27; width:sheet.colWidth; horizontalAlignment:Text.AlignHCenter
                text:modelData; font.pixelSize:11; color:Pearl.muted }
        }
        Repeater {
            model:42
            Item {
                required property int index
                objectName:"rangeDay"+index
                readonly property int dateNumber:index-period.leading+1
                readonly property real stamp:period.monthStart+(dateNumber-1)*86400000
                readonly property bool selected:stamp>=period.first && stamp<=period.last
                readonly property bool endpoint:stamp===period.first || stamp===period.last
                visible:dateNumber>=1 && dateNumber<=period.lastDay
                x:(index%7)*sheet.colWidth; y:45+Math.floor(index/7)*sheet.rowHeight
                width:sheet.colWidth; height:sheet.rowHeight
                Rectangle { visible:parent.selected; anchors.fill:parent; anchors.topMargin:1; anchors.bottomMargin:1
                    color:parent.endpoint ? Pearl.accent : Pearl.soft; radius:parent.endpoint ? 4 : 0 }
                Text { anchors.centerIn:parent; text:parent.dateNumber; font.pixelSize:12
                    color:parent.endpoint ? "white" : parent.selected ? Pearl.active : Pearl.muted
                    font.weight:parent.selected ? Font.DemiBold : Font.Normal }
            }
        }
    }
}
