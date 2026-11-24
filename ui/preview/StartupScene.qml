import QtQuick
import QtQuick.Controls
import "Pearl.js" as Pearl

FocusScope {
    id: scene
    required property real progress
    required property Text brandTarget
    signal skipRequested()

    function phase(start,end) {
        const t=Math.min(1,Math.max(0,(progress-start)/(end-start)))
        return t*t*(3-2*t)
    }
    function mix(a,b,t) { return a+(b-a)*t }
    readonly property real wordIn: phase(.69,.77)
    readonly property real travel: phase(.79,.985)
    readonly property real workspaceReveal: phase(.82,.985)
    readonly property real mapScale: Math.min(width*.86/752,height*.66/336,1.38)
    readonly property real centerY: height*.47
    readonly property point landing: {
        // Re-evaluate the navigation label's scene position during flight and resize.
        const frame=progress, w=width, h=height
        return brandTarget.mapToItem(scene,0,0)
    }
    focus: visible
    Keys.onEscapePressed: event => { event.accepted=true; skipRequested() }
    Rectangle { anchors.fill:parent; color:Pearl.paper; opacity:1-scene.workspaceReveal }
    MouseArea { anchors.fill:parent; acceptedButtons:Qt.AllButtons }

    Item {
        id:tile; width:752; height:336; scale:scene.mapScale
        x:(scene.width-width)/2; y:scene.centerY-height/2
        opacity:1-scene.wordIn; visible:opacity>0
        Item {
            id:camera; objectName:"introCamera"
            readonly property real focusT:scene.phase(.12,.365)
            width:tile.width; height:tile.height; transformOrigin:Item.TopLeft
            readonly property real zoom:2.12
            readonly property point focusPoint:Qt.point(575,128)
            scale:scene.mix(1,zoom,focusT)
            x:tile.width/2-scene.mix(tile.width/2,focusPoint.x,focusT)*scale
            y:tile.height/2-scene.mix(tile.height/2,focusPoint.y,focusT)*scale
            Item {
                objectName:"introGrainWorld"; anchors.fill:parent
                opacity:1-scene.phase(.50,.715); visible:opacity>0
                Image {
                    objectName:"introWorldWide"; anchors.fill:parent
                    source:scene.visible ? "assets/intro-grain-world.png" : ""
                    smooth:true; mipmap:true; opacity:1-camera.focusT; visible:opacity>0
                    onStatusChanged:if(status===Image.Error && scene.visible) scene.skipRequested()
                }
                Image {
                    objectName:"introWorldClose"; anchors.fill:parent
                    source:scene.visible ? "assets/intro-grain-neighbors.png" : ""
                    smooth:true; mipmap:true; opacity:camera.focusT; visible:opacity>0
                    onStatusChanged:if(status===Image.Error && scene.visible) scene.skipRequested()
                }
            }
            Image {
                objectName:"introGrainChina"
                width:tile.width/camera.zoom; height:tile.height/camera.zoom
                x:camera.focusPoint.x-width/2; y:camera.focusPoint.y-height/2
                source:scene.visible ? "assets/intro-grain-china.png" : ""
                smooth:true; mipmap:true
                opacity:1-scene.phase(.47,.49); visible:opacity>0
                onStatusChanged:if(status===Image.Error && scene.visible) scene.skipRequested()
            }
        }
        Item {
            // Clip the sprite sheet, not the geography panning across the window.
            anchors.fill:parent; clip:true
            Image {
                id:flow; objectName:"introGrainFlow"
                readonly property int frame:Math.round(29*Math.min(1, Math.max(0,(scene.progress-.49)/.26)))
                source:scene.visible ? "assets/intro-grain-flow.png" : ""
                width:tile.width*5; height:tile.height*6
                x:-(frame%5)*tile.width; y:-Math.floor(frame/5)*tile.height
                opacity:scene.phase(.47,.49)
                onStatusChanged:if(status===Image.Error && scene.visible) Qt.callLater(function(){if(scene.visible)scene.skipRequested()})
            }
        }
    }
    TextMetrics { id:metrics; font:scene.brandTarget.font; text:scene.brandTarget.text }
    Text {
        id:word; objectName:"introTitle"
        text:scene.brandTarget.text; font:scene.brandTarget.font; color:scene.brandTarget.color
        readonly property rect ink:metrics.tightBoundingRect
        readonly property real largeScale:252*scene.mapScale/Math.max(1,ink.width)
        transformOrigin:Item.TopLeft
        scale:scene.mix(largeScale,1,scene.travel)
        x:scene.mix(scene.width/2-(ink.x+ink.width/2)*largeScale,scene.landing.x,scene.travel)
        y:scene.mix(scene.centerY-(baselineOffset+ink.y+ink.height/2)*largeScale,scene.landing.y,scene.travel)
        opacity:scene.wordIn; Accessible.ignored:true
    }
    AbstractButton {
        id:skip; objectName:"skipIntro"; text:"跳过"
        anchors.right:parent.right; anchors.rightMargin:26; anchors.bottom:parent.bottom; anchors.bottomMargin:20
        width:52; height:32; hoverEnabled:true; opacity:1-scene.travel
        background:Rectangle { radius:5; color:skip.hovered ? Pearl.neutral : "transparent"; border.color:skip.activeFocus ? Pearl.ink : "transparent" }
        contentItem:Text { text:skip.text; font.pixelSize:12; color:Pearl.muted; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter }
        onClicked:scene.skipRequested()
    }
}
