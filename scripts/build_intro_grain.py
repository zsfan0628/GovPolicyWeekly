"""Bake the fine-grained world and its wordmark transition; not needed at runtime."""
from math import cos, pi, radians, sin
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw, ImageFont
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "ui/preview/assets"
W, H, COUNT, COLS, SCALE = 752, 336, 56, 8, 3
LEFT, TOP, TILE_W, TILE_H = 156, 32, 440, 248
# Camera center in world-tile pixels and final zoom (also used in StartupScene).
FOCUS_X, FOCUS_Y, ZOOM = 575, 128, 2.12
WORLD_INK, FOCUS_INK = "#746c70", "#845e69"


def alpha_mask(filename, w, h):
    image = QImage(w, h, QImage.Format_RGBA8888)
    image.fill(Qt.transparent)
    svg = QSvgRenderer(str(ASSETS / filename))
    assert svg.isValid()
    painter = QPainter(image)
    svg.render(painter)
    painter.end()
    return Image.frombytes("RGBA", (w, h), image.constBits()).getchannel("A")


def geo(x,y):
    lat = 90-(y-3)*180/(H-6)
    lon = (x-W/2)*180/((W/2-6)*(.80+.20*cos(radians(lat))))
    return lon,lat


def grains():
    land = alpha_mask("world-outline.svg", 2160, 1080)
    china = alpha_mask("china-region.svg", 574, 410)
    rng = Random(721)
    context, focus = [], []
    # One geographic lattice: zoom spreads existing points instead of adding new ones.
    dx,dy = 5.10,5.05
    for row in range(int((H-10)/dy)):
        for col in range(int((W-12)/dx)):
            x = 9 + (col + rng.uniform(-.035,.035))*dx
            y = 7 + (row + rng.uniform(-.035,.035))*dy
            lon,lat = geo(x,y)
            if abs(lon)>=180 or abs(lat)>=90:
                continue
            cx, cy = int((lon-70)*8.2), int((56-lat)*10)
            east = 0<=cx<574 and 0<=cy<410 and china.getpixel((cx,cy))>128
            if east:
                fx,fy = (x-FOCUS_X)*ZOOM+W/2,(y-FOCUS_Y)*ZOOM+H/2
                focus.append((fx,fy,rng.uniform(.88,1.03),rng.uniform(162,182),rng.uniform(-1,1)))
            elif land.getpixel((int((lon+180)*6),int((90-lat)*6)))>=128:
                context.append((x,y,rng.uniform(.43,.53),rng.uniform(63,77)*(.6 if lat < -65 else 1)))
    return context, sorted(focus,key=lambda p:p[0]+.24*p[1])


def letters(n):
    font = ImageFont.truetype(str(ROOT/"assets/fonts/SourceHanSerifCN-SemiBold.otf"),64)
    glyphs = "政策周报"
    left,top,right,bottom = font.getbbox(glyphs)
    mask = Image.new("L",(W,H))
    ImageDraw.Draw(mask).text(((W-left-right)/2,(H-top-bottom)/2),glyphs,font=font,fill=255)
    candidates = [(x,y) for y in range(H) for x in range(W) if mask.getpixel((x,y))>132]
    return sorted(Random(27).sample(candidates,n),key=lambda p:p[0]+.24*p[1])


def ink(alpha,color):
    image = Image.new("RGBA",alpha.size,color)
    image.putalpha(alpha)
    return image


def ease(x):
    x = min(1,max(0,x))
    return x*x*(3-2*x)


def ribbon_point(p, lane, ribbon, depth):
    front = ease((p-.16)/.73)
    wx = 253+251*front+(lane-.5)*162
    wave = 2*pi*(front*.77-lane*.74)+ribbon*.81
    wy = H/2-16-34*sin(wave) + (8+16*sin(pi*front))*cos(wave+depth)
    return wx+11*sin(depth+wave),wy


def sweep(p, grain, dest, ribbon, depth):
    x,y = grain[:2]
    u,v = dest
    lane = (x-268)/230
    gather = ease((p-.05*lane)/.36)
    land = ease((p-(.28+.42*(u-248)/256))/.29)
    air = gather*(1-land)
    wx,wy = ribbon_point(p,lane,ribbon,depth)
    xx = (x*(1-gather)+wx*gather)*(1-land)+u*land
    yy = (y*(1-gather)+wy*gather)*(1-land)+v*land
    return xx, yy, air


def flow_sheet(source):
    # Satellites exist only while moving: the geographic still keeps its original dot count.
    rng = Random(413)
    targets = letters(len(source)*5)
    palette = [(132,94,105),(167,116,131),(114,108,125),(190,149,137),(211,182,179)]
    particles = []
    for i,grain in enumerate(source):
        for k in range(5):
            depth = (grain[1]-110)/64 + rng.uniform(-.35,.35)
            particles.append((grain,targets[5*i+k],k,depth,rng.uniform(-.035,.035)))
    atlas = Image.new("RGBA",(TILE_W*COLS,TILE_H*(COUNT//COLS)))
    for f in range(COUNT):
        t = f/(COUNT-1)
        tile = Image.new("RGBA",(TILE_W*SCALE,TILE_H*SCALE))
        pen = ImageDraw.Draw(tile)
        # A few fine strands keep the leading edge readable between individual grains.
        strength = ease((t-.23)/.15)*(1-ease((t-.57)/.20))
        if strength>0:
            for strand in range(6):
                path = []
                for step in range(65):
                    lane = .10+.80*step/64
                    x,y = ribbon_point(t,lane,strand%2,(strand//2-1)*.48)
                    path.append(((x-LEFT)*SCALE,(y-TOP)*SCALE))
                pen.line(path,fill=(*palette[strand%5],round(74*strength)),width=2)
        for grain,dest,k,depth,delay in particles:
            p = t + delay*sin(pi*t)
            x,y,air = sweep(p,grain,dest,k%2,depth)
            opacity = grain[3] if k==0 else 168*air
            if opacity<2:
                continue
            x,y = (x-LEFT)*SCALE,(y-TOP)*SCALE
            radius = SCALE*(grain[2] if k==0 else .62+.22*cos(depth))
            rgb = palette[k]
            if air>.04:
                # A short tangent trail gives direction without smearing the map or the type.
                tx,ty,_ = sweep(max(0,p-.009),grain,dest,k%2,depth)
                pen.line(((tx-LEFT)*SCALE,(ty-TOP)*SCALE,x,y),fill=(*rgb,round(opacity*.54*air)),width=2)
            pen.ellipse((x-radius,y-radius,x+radius,y+radius),fill=(*rgb,round(opacity)))
        atlas.paste(tile.resize((TILE_W,TILE_H),Image.Resampling.LANCZOS),
                    ((f%COLS)*TILE_W,(f//COLS)*TILE_H))
    atlas.save(ASSETS/"intro-grain-flow.png",optimize=True)


def welcome_sheet():
    """Only the airborne ink is baked. Qt draws the actual letters at screen resolution."""
    w,h,cols,frames = 432,156,7,84
    rng = Random(930)
    colors = [(112,76,90),(155,105,125),(180,139,146),(120,114,137),(199,169,158)]
    stream = [(rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(0,2*pi),
               rng.uniform(.45,1.2),colors[i%5]) for i in range(420)]
    font = ImageFont.truetype(str(ROOT/"assets/fonts/SourceHanSerifCN-SemiBold.otf"),84)
    mask = font.getmask("Welcome",mode="L")
    glyph = Image.frombytes("L",mask.size,bytes(mask))
    glyph = glyph.crop(glyph.getbbox())
    glyph = glyph.resize((266,round(266*glyph.height/glyph.width)),Image.Resampling.LANCZOS)
    sites = [(83+x,(h-glyph.height)/2+y) for y in range(glyph.height)
             for x in range(glyph.width) if glyph.getpixel((x,y))>128]
    dust = [(x,y,rng.uniform(16,50),rng.uniform(-27,27),rng.uniform(0,2*pi))
            for x,y in rng.sample(sites,480)]
    sheet = Image.new("RGBA",(w*cols,h*(frames//cols)))
    for f in range(frames):
        t = f/(frames-1)
        tile = Image.new("RGBA",(w*SCALE,h*SCALE))
        pen = ImageDraw.Draw(tile)
        lead = ease((t-.035)/.52)
        strength = ease(t/.09)*(1-ease((t-.48)/.14))
        if strength:
            for i,(lane,depth,phase,r,color) in enumerate(stream):
                fan = sin(pi*(lane+1)/2)
                width = (12+44*sin(pi*lead))*strength
                x = 83+266*lead+lane*width+4*depth*fan
                twist = 2*pi*(lead*.93-lane*.36)
                y = h/2-22*sin(twist)+fan*((-1 if i%2 else 1)*8*cos(twist)+7*cos(twist+phase)+depth*4)
                a = round((112+68*(1-abs(depth)))*strength*(.38+.62*fan))
                pen.line(((x-4*strength)*SCALE,(y+2*cos(twist)*strength)*SCALE,x*SCALE,y*SCALE),
                         fill=(*color,a//2),width=2)
                pen.ellipse(((x-r)*SCALE,(y-r)*SCALE,(x+r)*SCALE,(y+r)*SCALE),fill=(*color,a))
        # Each fragment lifts off when the erasing edge reaches its original letter.
        for i,(x,y,vx,vy,phase) in enumerate(dust):
            age = (ease((t-.68)/.27)-(x-83)/266)
            if not 0<age<.7:
                continue
            life = age/.7
            u = x+vx*life
            v = y+vy*life+9*sin(pi*life)*sin(phase)
            r = .95-.5*life
            a = round(186*(1-ease(life))*(1-ease((t-.94)/.06)))
            pen.ellipse(((u-r)*SCALE,(v-r)*SCALE,(u+r)*SCALE,(v+r)*SCALE),
                        fill=(*colors[i%5],a))
        sheet.paste(tile.resize((w,h),Image.Resampling.LANCZOS),((f%cols)*w,(f//cols)*h))
    sheet.save(ASSETS/"intro-welcome.png",optimize=True)


def bake():
    context,source = grains()
    # Keep dot diameter nearly constant on screen as the camera spreads the grid.
    for name,size in (("world",1.7),("neighbors",1.7/ZOOM)):
        s = 2*SCALE
        world = Image.new("L",(W*s,H*s))
        pen = ImageDraw.Draw(world)
        for x,y,r,alpha in context:
            r *= size
            pen.ellipse(((x-r)*s,(y-r)*s,(x+r)*s,(y+r)*s),fill=round(alpha))
        world = world.resize((W*SCALE,H*SCALE),Image.Resampling.LANCZOS)
        ink(world,WORLD_INK).save(ASSETS/f"intro-grain-{name}.png",optimize=True)
    alpha = Image.new("L",(W*SCALE,H*SCALE))
    pen = ImageDraw.Draw(alpha)
    for x,y,r,weight,_ in source:
        pen.ellipse(((x-r)*SCALE,(y-r)*SCALE,(x+r)*SCALE,(y+r)*SCALE),fill=round(weight))
    ink(alpha,FOCUS_INK).save(ASSETS/"intro-grain-china.png",optimize=True)
    flow_sheet(source)
    welcome_sheet()
    print(f"{len(source)} grains; {COUNT} transition frames; {W*SCALE}px opening")


if __name__=="__main__":
    bake()
