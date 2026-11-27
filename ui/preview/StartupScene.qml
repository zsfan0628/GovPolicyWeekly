import QtQuick
import QtQuick.Controls
import QtQuick.Shapes
import "Pearl.js" as Pearl

FocusScope {
    id: scene
    required property real progress
    required property Text brandTarget
    signal skipRequested()
    function phase(start,end) {
        const t=Math.max(0,Math.min(1,(progress-start)/(end-start)))
        return t*t*(3-2*t)
    }
    function mix(a,b,t) { return a+(b-a)*t }
    readonly property real stageScale:Math.min(width*.88/544,height*.62/236,1.85)
    readonly property real centerY:height*.47
    readonly property real travel:phase(.817,.975)
    readonly property real handoff:phase(.987,.998)
    readonly property real workspaceReveal:phase(.805,.855)
    readonly property real irisRadius:(Math.sqrt(width*width+height*height)/2+2)*phase(.855,.987)
    readonly property point landing:{
        const frame=progress,w=width,h=height
        return brandTarget.mapToItem(scene,0,0)
    }
    focus:visible
    Keys.onEscapePressed:event=>{event.accepted=true;skipRequested()}
    Rectangle { anchors.fill:parent; color:"#100f14"; visible:scene.irisRadius===0 }
    Shape {
        anchors.fill:parent; visible:scene.irisRadius>0 && scene.progress<.987; clip:true
        ShapePath {
            fillRule:ShapePath.OddEvenFill; fillColor:"#100f14"; strokeWidth:-1
            startX:0; startY:0
            PathLine { x:scene.width; y:0 }
            PathLine { x:scene.width; y:scene.height }
            PathLine { x:0; y:scene.height }
            PathLine { x:0; y:0 }
            PathAngleArc {
                centerX:scene.width/2; centerY:scene.height/2
                radiusX:scene.irisRadius; radiusY:scene.irisRadius; startAngle:0; sweepAngle:360
                moveToStart:true
            }
        }
    }
    MouseArea { anchors.fill:parent; acceptedButtons:Qt.AllButtons }
    WelcomeSweep {
        id:stage; objectName:"welcomeSweep"
        progress:scene.progress; playing:scene.visible
        scale:scene.stageScale; x:(scene.width-width)/2; y:scene.centerY-height/2
        onUnavailable:if(scene.visible) scene.skipRequested()
    }
    TextMetrics { id:metrics; font:scene.brandTarget.font; text:scene.brandTarget.text }
    Text {
        id:word; objectName:"introTitle"
        text:scene.brandTarget.text; font:scene.brandTarget.font
        renderTypeQuality:Text.VeryHighRenderTypeQuality
        readonly property color light:"#f6eff4"
        readonly property color dark:scene.brandTarget.color
        readonly property real dx:x+(ink.x+ink.width/2)*scale-scene.width/2
        readonly property real dy:y+(baselineOffset+ink.y+ink.height/2)*scale-scene.height/2
        readonly property real mixInk:scene.irisRadius===0 ? 0 : scene.progress>=.987 ? 1 :
            Math.max(0,Math.min(1,.5+(scene.irisRadius-Math.sqrt(dx*dx+dy*dy))/Math.max(1,ink.width*scale)))
        color:mixInk>=1 ? dark : Qt.rgba(scene.mix(light.r,dark.r,mixInk),scene.mix(light.g,dark.g,mixInk),scene.mix(light.b,dark.b,mixInk),1)
        readonly property rect ink:metrics.tightBoundingRect
        readonly property real largeScale:230*scene.stageScale/Math.max(1,ink.width)
        transformOrigin:Item.TopLeft
        scale:scene.mix(largeScale,1,scene.travel)
        x:scene.mix(scene.width/2-(ink.x+ink.width/2)*largeScale,scene.landing.x,scene.travel)
        y:scene.mix(scene.centerY-(baselineOffset+ink.y+ink.height/2)*largeScale,scene.landing.y,scene.travel)
        opacity:scene.phase(.735,.779)*(1-scene.handoff); Accessible.ignored:true
    }
    AbstractButton {
        id:skip; objectName:"skipIntro"; text:"跳过"
        anchors.right:parent.right; anchors.rightMargin:26; anchors.bottom:parent.bottom; anchors.bottomMargin:20
        width:52; height:32; hoverEnabled:true; opacity:1-scene.travel
        background:Rectangle { radius:5; color:skip.hovered ? "#353239" : "transparent"; border.color:skip.activeFocus ? "#dfd9e3" : "transparent" }
        contentItem:Text { text:skip.text; font.pixelSize:12; color:"#bdb7c3"; horizontalAlignment:Text.AlignHCenter; verticalAlignment:Text.AlignVCenter }
        onClicked:scene.skipRequested()
    }
}
