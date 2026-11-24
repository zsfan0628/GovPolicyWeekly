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
W, H, COUNT, COLS, SCALE = 752, 336, 30, 5, 3
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
    target = letters(len(source))
    atlas = Image.new("L",(W*COLS,H*(COUNT//COLS)))
    for frame in range(COUNT):
        alpha = Image.new("L",(W*SCALE,H*SCALE))
        pen = ImageDraw.Draw(alpha)
        for (x,y,r,weight,j),(u,v) in zip(source,target):
            t = min(1,max(0,(frame/(COUNT-1)-.09*x/W)/.91))
            t = t*t*(3-2*t)
            arc = sin(pi*t)
            xx = SCALE*(x+(u-x)*t+arc*8*j)
            yy = SCALE*(y+(v-y)*t+arc*(16*sin(x*.019)+5*j))
            rr = SCALE*(r+(1.06-r)*t)
            pen.ellipse((xx-rr,yy-rr,xx+rr,yy+rr), fill=round(weight+(230-weight)*t))
        if frame==0:
            ink(alpha,FOCUS_INK).save(ASSETS/"intro-grain-china.png",optimize=True)
        atlas.paste(alpha.resize((W,H),Image.Resampling.LANCZOS),((frame%COLS)*W,(frame//COLS)*H))
    ink(atlas,FOCUS_INK).save(ASSETS/"intro-grain-flow.png",optimize=True)
    print(f"{len(source)} grains; {COUNT} transition frames; {W*SCALE}px opening")


if __name__=="__main__":
    bake()
