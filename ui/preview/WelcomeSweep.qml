import QtQuick

Item {
    id:stage
    required property real progress
    required property bool playing
    signal unavailable()
    width:544; height:236
    function smooth(a,b) {
        const t=Math.max(0,Math.min(1,(progress-a)/(b-a)))
        return t*t*(3-2*t)
    }
    readonly property real resolved:smooth(.365,.385)
    readonly property int depositFrame:Math.round(111*Math.min(1,stage.progress/.365))
    readonly property real spin:Math.min(1,Math.max(0,(progress-.42)/.40))
    Item {
        id:mask; objectName:"welcomeInk"
        x:44; height:stage.height; clip:true
        width:456*Math.min(1,Math.max(0,1-stage.spin/.24))
        visible:width>0
        Item {
            id:label; objectName:"welcomeWord"
            readonly property string text:"Welcome to Policy Weekly"
            width:456; height:parent.height
            Accessible.name:text
            Repeater {
                model:19
                Item {
                    id:strip; required property int index
                    width:24; height:image.sourceSize.height/80
                    x:index*24; anchors.verticalCenter:parent.verticalCenter; clip:true
                    readonly property int first:Math.floor(111*(.24+.63*index/19))-1
                    readonly property int slot:Math.max(0,Math.min(19,stage.depositFrame-first))
                    Image {
                        id:image; source:stage.playing ? "assets/cinema-word.png" : ""
                        width:456; height:sourceSize.height/4; x:-strip.x; y:-strip.slot*strip.height
                        smooth:true
                        onStatusChanged:if(status===Image.Error && stage.playing) stage.unavailable()
                    }
                }
            }
        }
    }
    Item {
        width:544; height:174; y:4; clip:true
        opacity:1-stage.resolved
        visible:opacity>0
        Image {
            objectName:"introRibbon"
            readonly property int frame:stage.depositFrame
            source:stage.playing ? "assets/cinema-ribbon.png" : ""
            width:parent.width*7; height:parent.height*16
            x:-(frame%7)*parent.width; y:-Math.floor(frame/7)*parent.height
            onStatusChanged:if(status===Image.Error && stage.playing) stage.unavailable()
        }
    }
    Item {
        anchors.fill:parent; clip:true; visible:stage.spin>0 && stage.spin<1
        Image {
            objectName:"introSpiral"
            readonly property int frame:Math.round(stage.spin*83)
            source:stage.playing ? "assets/cinema-spiral.png" : ""
            asynchronous:true
            width:parent.width*7; height:parent.height*12
            x:-(frame%7)*parent.width; y:-Math.floor(frame/7)*parent.height
            onStatusChanged:if(status===Image.Error && stage.playing) stage.unavailable()
        }
    }
}
