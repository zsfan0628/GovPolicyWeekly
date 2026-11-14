import QtQuick
import QtQuick.Controls

Item {
    id: startup
    property real progress: 0
    property real departure: 0
    property bool reducedMotion: false
    property Item brandTarget: null
    property point brandPosition: Qt.point(78, 25)
    readonly property var world: JSON.parse(preview.introMapJson)
    readonly property var glyphs: JSON.parse(preview.introPointsJson)
    readonly property var origins: world.filter(p => p.china)
    readonly property real titleWidth: Math.min(360, width * 0.38)
    readonly property real titleHeight: titleWidth / preview.introTitleAspect
    readonly property real zoom: smooth((progress - 0.22) / 0.30)
    readonly property real morph: smooth((progress - 0.51) / 0.34)
    readonly property real solid: smooth((progress - 0.84) / 0.12)
    signal skipRequested()
    function clamp(t) { return Math.max(0, Math.min(1, t)) }
    function smooth(t) { t=clamp(t); return t*t*(3-2*t) }
    function mapPoint(p) {
        const span=Math.min(width*0.86, 1050)*(1+1.3*zoom)
        return Qt.point(width/2 + (p.x-(0.5+0.30*zoom))*span,
                        height*0.44 + (p.y-(0.48-0.17*zoom))*span/2)
    }
    function destination() {
        return brandTarget ? brandTarget.mapToItem(startup, 0, 3) : Qt.point(28,28)
    }
    onProgressChanged: particles.requestPaint()
    onDepartureChanged: { brandPosition = destination(); particles.requestPaint() }
    onWidthChanged: particles.requestPaint()
    onHeightChanged: particles.requestPaint()
    Rectangle { anchors.fill: parent; color: "#f4f8f5"; opacity: 1-startup.departure }
    Canvas {
        id: particles; objectName: "introParticles"
        anchors.fill: parent; renderTarget: Canvas.Image
        opacity: 1-startup.departure
        onAvailableChanged: requestPaint()
        onPaint: {
            const c=getContext("2d"); c.clearRect(0,0,width,height)
            const reveal=startup.smooth(startup.progress/0.20)
            for (let i=0;i<startup.world.length;i++) {
                const p=startup.world[i], xy=startup.mapPoint(p)
                if (xy.x < 0 || xy.x > width || xy.y < 0 || xy.y > height) continue
                const edge=Math.min(1,xy.x/70,(width-xy.x)/70,xy.y/60,(height-xy.y)/60)
                const seed=(i*0.6180339)%1
                const size=1.1+seed*0.55+startup.zoom*0.15
                c.globalAlpha=edge*reveal*(p.china ? 0.6 : 0.30)*(1-startup.morph*0.86)
                c.fillStyle=p.china ? "#41866f" : "#879b92"
                c.beginPath(); c.arc(xy.x, xy.y+(1-reveal)*7*Math.sin(i), size,0,Math.PI*2); c.fill()
            }
            const nodes=[[116.4,39.9],[126.64,45.75],[118.8,32.06],[114.3,30.59],[120.86,32.01]]
            for(let i=0;i<nodes.length;i++) {
                const alpha=startup.smooth((startup.progress-0.36-i*0.018)/0.09)*(1-startup.smooth((startup.progress-0.55)/0.1))
                const p=startup.mapPoint({x:(nodes[i][0]+180)/360,y:(90-nodes[i][1])/180})
                c.globalAlpha=alpha; c.strokeStyle="#518f79"; c.lineWidth=1
                c.beginPath(); c.arc(p.x,p.y,6,0,Math.PI*2); c.stroke()
                c.fillStyle="#296c55"; c.beginPath(); c.arc(p.x,p.y,2,0,Math.PI*2); c.fill()
            }
            if(startup.progress>0.51 && startup.origins.length>0) {
                for(let i=0;i<startup.glyphs.length;i++) {
                    const p=startup.glyphs[i], seed=(i*0.381966)%1
                    const from=startup.mapPoint(startup.origins[(i*37)%startup.origins.length])
                    const t=startup.smooth((startup.progress-0.51-seed*0.04)/0.31)
                    const toX=width/2+(p.x-0.5)*startup.titleWidth
                    const toY=height*0.45+(p.y-0.5)*startup.titleHeight
                    const x=from.x+(toX-from.x)*t
                    const y=from.y+(toY-from.y)*t-Math.sin(t*Math.PI)*(16+seed*30)
                    c.globalAlpha=startup.clamp((startup.progress-0.51)*16)*(1-startup.solid)*0.85
                    c.fillStyle=i%9===0 ? "#6d9e8a" : "#234b3f"
                    c.fillRect(x,y,1.3,1.3)
                }
            }
            c.globalAlpha=1
        }
    }
    Image {
        id: title; objectName: "introSolidTitle"
        source: "image://intro/title"
        readonly property point target: startup.brandPosition
        width: startup.titleWidth + ((startup.brandTarget ? startup.brandTarget.width : 68)-startup.titleWidth)*startup.departure
        height: width/preview.introTitleAspect
        x: (startup.width-startup.titleWidth)/2*(1-startup.departure)+target.x*startup.departure
        y: (startup.height*0.45-startup.titleHeight/2)*(1-startup.departure)+target.y*startup.departure
        opacity: startup.solid
        smooth: true
    }
    Text {
        anchors.horizontalCenter: parent.horizontalCenter
        y: parent.height*0.45 + startup.titleHeight/2 + 25
        text: "POLICY WEEKLY"; font.pixelSize: 12; color: "#82958b"
        opacity: startup.smooth((startup.progress-0.77)/0.18)*(1-startup.departure)
    }
    AppButton {
        objectName: "skipIntro"
        anchors.right: parent.right; anchors.rightMargin: 28; anchors.bottom: parent.bottom; anchors.bottomMargin: 24
        text: "跳过"; tone: "ghost"; compact: true
        opacity: 1-startup.departure
        onClicked: startup.skipRequested()
    }
    Keys.onEscapePressed: skipRequested()
}
