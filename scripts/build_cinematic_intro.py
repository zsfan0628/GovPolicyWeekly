"""Bake the original light ribbon and spiral. No renderer or video codec ships with the app."""
from math import ceil, cos, floor, pi, sin, sqrt
from pathlib import Path
from random import Random

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "ui/preview/assets"
PHRASE = "Welcome to Policy Weekly"
W, H, S = 544, 236, 2
COLORS = [(104,155,255),(155,186,255),(215,218,255),(255,218,168),(255,245,229)]


def ease(t):
    t = min(1,max(0,t))
    return t*t*(3-2*t)


def glyphs(text, face, width, scale):
    f = ImageFont.truetype(str(ROOT/"assets/fonts"/face),max(132,width*scale//8))
    raw = f.getmask(text,mode="L")
    mask = Image.frombytes("L",raw.size,bytes(raw))
    mask = mask.crop(mask.getbbox())
    return mask.resize((width*scale,round(width*scale*mask.height/mask.width)),Image.Resampling.LANCZOS)


def emissive(layer, glow=1):
    bloom = layer.filter(ImageFilter.GaussianBlur(3))
    light = ImageChops.add(layer,bloom)
    if glow:
        light = ImageChops.add(light,bloom.filter(ImageFilter.GaussianBlur(6)).point(lambda p:p*.85))
    r,g,b = light.split()
    alpha = ImageChops.lighter(r,ImageChops.lighter(g,b))
    return Image.merge("RGBa",(r,g,b,alpha)).convert("RGBA")


def word_plate(mask):
    # A silver face with cool shadows; retain a 3x edge mask for Retina displays.
    rgb = Image.new("RGB",mask.size)
    pen = ImageDraw.Draw(rgb)
    for y in range(mask.height):
        t = y/max(1,mask.height-1)
        color = tuple(round(a+(b-a)*t) for a,b in zip((255,248,242),(150,169,225)))
        pen.line((0,y,mask.width,y),fill=color)
    rgb.putalpha(mask)
    return rgb


def deposition(plate):
    # Each ink patch has exactly one carrier. Only a landing may add it to the word.
    n,cols,top,h = 112,7,4,174
    origin = (32.,148.-top)
    resolution,strip,slots=4,24,20
    baseline=H/2-top-plate.height/(2*resolution)
    rng = Random(234)
    parcels = []
    for y in range(0,plate.height,8):
        for x in range(0,plate.width,8):
            rect = (x,y,min(x+8,plate.width),min(y+8,plate.height))
            patch = plate.crop(rect)
            box = patch.getchannel("A").getbbox()
            if box is None:
                continue
            tx = 44+(x+(box[0]+box[2])/2)/resolution
            ty = baseline+(y+(box[1]+box[3])/2)/resolution
            u = (tx-44)/456
            band = rng.randrange(2)
            depth = rng.gauss(0,.43)
            birth = .085+.43*u*rng.uniform(.12,1)+rng.uniform(0,.064)
            arrival = .24+.63*u+rng.uniform(0,.105)
            high = (.08+.92*u)**.64*(63+83*band+23*depth)
            color = COLORS[(0 if band else 3) if rng.random()<.73 else 4]
            parcels.append((birth,arrival,tx,ty,high,depth,rng.uniform(.28,.80),color,
                            rect))

    sheet=Image.new("RGBA",(W*cols,h*(n//cols)))
    # Each 24-unit strip changes for fewer than 20 frames. Keep its whole
    # deposition history at 4x without allocating 112 full-size text plates.
    strip_px=strip*resolution
    ink_sheet=Image.new("RGBA",(plate.width,slots*plate.height))
    for i in range(456//strip):
        first=floor((n-1)*(.24+.63*i/19))-1
        formed=Image.new("RGBA",(strip_px,plate.height))
        landings={}
        for _,arrival,*_,box in parcels:
            if box[0]//strip_px!=i: continue
            f=ceil((n-1)*arrival)-first
            assert 0<=f<slots
            landings.setdefault(f,[]).append(box)
        for slot in range(slots):
            for box in landings.get(slot,[]):
                formed.paste(plate.crop(box),(box[0]-i*strip_px,box[1]))
            ink_sheet.paste(formed,(i*strip_px,slot*plate.height))
        assert formed.getchannel("A").tobytes()==plate.crop((i*strip_px,0,(i+1)*strip_px,plate.height)).getchannel("A").tobytes()
    ink_sheet.save(ASSETS/"cinema-word.png",optimize=True)
    for f in range(n):
        p=f/(n-1)
        light=Image.new("RGB",(W*S,h*S)); pen=ImageDraw.Draw(light)
        for birth,arrival,x,y,high,depth,r,c,_ in parcels:
            if p<birth or p>arrival+.052:
                continue
            q=min(1,(p-birth)/(arrival-birth))
            def pos(v):
                # Shared launch tangent; two folded sheets fan out, then decelerate into ink.
                a=1-(1-v)**1.48
                lift=4*v*(1-v)*(1-.25*v)
                return (origin[0]+(x-origin[0])*a+7*depth*lift,
                        origin[1]+(y-origin[1])*a-high*lift*(.78+.22*cos(2*pi*v+depth)))
            xx,yy=pos(q)
            tailx,taily=pos(max(0,q-.012/(arrival-birth)))
            heat=(.33+.36*min(1,abs(depth)+.2)+.22*(r>.73))*(1-ease((p-arrival)/.052))
            flash=ease((q-.83)/.17)
            rgb=tuple(round((a+(248-a)*flash)*heat) for a in c)
            pen.line((tailx*S,taily*S,xx*S,yy*S),fill=tuple(round(k*.55) for k in rgb),width=1)
            pen.ellipse(((xx-r)*S,(yy-r)*S,(xx+r)*S,(yy+r)*S),fill=rgb)
        # The emitter stays anchored and burns down only after the last launch.
        power=ease((p+.016)/.055)*(1-ease((p-.49)/.15))
        if power>0:
            x,y=origin
            for radius,brightness in ((4.2,.10),(2.6,.28),(1.55,.76),(.82,1.0)):
                r=radius*(.5+.5*power)
                pen.ellipse(((x-r)*S,(y-r)*S,(x+r)*S,(y+r)*S),
                            fill=tuple(round(k*brightness*power) for k in (224,236,255)))
        frame=emissive(light.resize((W,h),Image.Resampling.LANCZOS))
        sheet.paste(frame,((f%cols)*W,(f//cols)*h))
    sheet.save(ASSETS/"cinema-ribbon.png",optimize=True)
    print(f"{len(parcels)} emitted glyph patches; {n} frames")


def samples(mask,width):
    m=mask.resize((width,round(width*mask.height/mask.width)),Image.Resampling.LANCZOS)
    return [(x+(W-m.width)/2,y+(H-m.height)/2) for y in range(m.height)
            for x in range(m.width) if m.getpixel((x,y))>112]


def swirl(en,cn):
    rng=Random(119); n,cols=84,7
    src,dst=samples(en,456),samples(cn,230)
    grains=[]
    for i in range(3200):
        x,y=rng.choice(src); u,v=rng.choice(dst)
        radius=rng.random()**(.84 if i%4 else .45)
        spin=(i%3)*2*pi/3+radius*6.3+rng.gauss(0,.48 if i%5==0 else .16)
        grains.append((x,y,u,v,radius,spin,rng.gauss(0,1),rng.random()))
    sheet=Image.new("RGBA",(W*cols,H*(n//cols)))
    for f in range(n):
        p=f/(n-1); tile=Image.new("RGB",(W*S,H*S)); pen=ImageDraw.Draw(tile)
        for x,y,u,v,r,a,z,j in grains:
            release=.24*(1-(x-(W-456)/2)/456)
            lift=ease((p-release)/.27)
            land=ease((p-.55-.10*j)/.32)
            opacity=ease((p-release+.005)/.045)*(1-ease((p-.87)/.13))
            if opacity<=0: continue
            theta=a+4.8*p
            xx=179*r*cos(theta); yy=79*r*sin(theta)+z*4*r
            sx=(1-lift)*x+lift*(W/2+xx+.19*yy)
            sy=(1-lift)*y+lift*(H/2+yy-.14*xx)
            sx+=(u-sx)*land; sy+=(v-sy)*land
            c=COLORS[(0 if cos(theta)<-.22 else 3) if j<.62 else (4 if j>.79 else 2)]
            rad=.28+.62*j*j
            color=tuple(round(k*opacity*(.24+.76*j)) for k in c)
            tail=lift*(1-land)*r
            pen.line(((sx+4*sin(theta)*tail)*S,(sy-1.9*cos(theta)*tail)*S,sx*S,sy*S),
                     fill=tuple(int(k*.58) for k in color),width=1)
            pen.ellipse(((sx-rad)*S,(sy-rad)*S,(sx+rad)*S,(sy+rad)*S),fill=color)
        sheet.paste(emissive(tile.resize((W,H),Image.Resampling.LANCZOS)),((f%cols)*W,(f//cols)*H))
    sheet.save(ASSETS/"cinema-spiral.png",optimize=True)


if __name__=="__main__":
    en=glyphs(PHRASE,"SourceHanSansCN-Medium.ttf",456,4)
    cn=glyphs("政策周报","SourceHanSerifCN-SemiBold.otf",230,2)
    deposition(word_plate(en)); swirl(en,cn)
