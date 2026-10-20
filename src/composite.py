"""2D compositor: turns the rendered 3D plates into the finished 1080x1920 ad.

Layers per frame (bottom -> top):
  3D plate (upscaled) -> particles (rain / bokeh / sparkles) -> cards & logo
  -> grade (vignette, grain) -> [transition blur applied to all of the above]
  -> captions (stay sharp through transitions, like the reference)

usage:
  python3 src/composite.py                 # full video -> build/video_noaudio.mp4
  python3 src/composite.py --frames 120,400  # stills -> build/stills/
"""
import argparse
import json
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "config", "timeline.json")))
W, H, FPS = TL["width"], TL["height"], TL["fps"]
FRAMES_DIR = os.path.join(ROOT, "build", "frames")

# ---------------------------------------------------------------- style
# Colours sampled from the reference (Oct-20Footage1)
ORANGE = (248, 100, 39)
ACC_ORANGE = (252, 152, 64)
RED = (217, 56, 47)
GREEN = (37, 190, 95)
CREAM = (247, 242, 235)
INK = (22, 22, 28)
GREY = (112, 106, 100)
WHITE = (255, 255, 255)

FD = "/usr/share/fonts/opentype/inter/"
_fonts = {}


def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        path = (FD + f"Inter-{weight}.otf" if weight != "Sym" else
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        _fonts[key] = ImageFont.truetype(path, size)
    return _fonts[key]


CAP_SIZE = 68
CAP_X, CAP_Y, CAP_LH, CAP_MAXW = 66, 140, 84, 950
CARD_Y = 380  # top of floating cards (below a 2-line caption)

SS = 3  # supersampling for shapes


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_out_back(t, s=1.4):
    t = clamp(t)
    t -= 1
    return t * t * ((s + 1) * t + s) + 1


def ease_in_out(t):
    t = clamp(t)
    return 3 * t * t - 2 * t * t * t


# ---------------------------------------------------------------- sprites
def rrect(w, h, r, fill, outline=None, width=0):
    """Anti-aliased rounded rectangle sprite (RGBA)."""
    im = Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, w * SS - 1, h * SS - 1), r * SS, fill=fill,
                        outline=outline, width=width * SS)
    return im.resize((w, h), Image.LANCZOS)


def circle(d, fill):
    im = Image.new("RGBA", (d * SS, d * SS), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((0, 0, d * SS - 1, d * SS - 1), fill=fill)
    return im.resize((d, d), Image.LANCZOS)


def with_shadow(sprite, blur=22, offset=(0, 14), alpha=0.55, pad=50):
    w, h = sprite.size
    out = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    a = sprite.split()[3].point(lambda v: int(v * alpha))
    sh = Image.new("RGBA", sprite.size, (0, 0, 0, 255))
    sh.putalpha(a)
    out.alpha_composite(sh, (pad + offset[0], pad + offset[1]))
    out = out.filter(ImageFilter.GaussianBlur(blur))
    out.alpha_composite(sprite, (pad, pad))
    return out, pad


def check_icon(size, bg, fg=WHITE):
    im = circle(size, bg)
    big = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    s = size * SS
    d.line([(s * 0.28, s * 0.52), (s * 0.44, s * 0.68), (s * 0.73, s * 0.35)], fill=fg,
           width=int(s * 0.11), joint="curve")
    im.alpha_composite(big.resize((size, size), Image.LANCZOS))
    return im


def phone_icon(size, fg=WHITE):
    im = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    f = font("Sym", int(size * SS * 0.95))
    d.text((size * SS / 2, size * SS / 2), "☎", font=f, fill=fg, anchor="mm")
    return im.resize((size, size), Image.LANCZOS)


def text_w(txt, f):
    return f.getlength(txt)


# ---------------------------------------------------------------- card builders
def card_item(title, sub, num, accent, check=False, w=900, h=136):
    accent_c = {"orange": ACC_ORANGE, "red": RED, "green": GREEN}[accent]
    card = rrect(w, h, 26, CREAM)
    bar = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bar.paste(rrect(30, h, 12, accent_c + (255,)), (0, 0))
    mask = rrect(w, h, 26, (255, 255, 255, 255)).split()[3]
    bar_cut = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bar_cut.paste(bar, (0, 0), mask)
    card.alpha_composite(bar_cut.crop((0, 0, 12, h)), (0, 0))
    d = ImageDraw.Draw(card)
    if check:
        card.alpha_composite(check_icon(64, GREEN + (255,)), (40, (h - 64) // 2))
    else:
        card.alpha_composite(circle(64, (232, 226, 216, 255)), (40, (h - 64) // 2))
        d.text((72, h // 2), num, font=font("Bold", 30), fill=(60, 56, 52), anchor="mm")
    tcol = RED if accent == "red" else INK
    d.text((130, 26), title, font=font("Bold", 50), fill=tcol)
    d.text((132, 88), sub, font=font("Medium", 28), fill=GREY)
    return with_shadow(card)


def tag_sprite(text, color):
    c = {"orange": ORANGE, "red": RED}[color]
    f = font("ExtraBold", 34)
    tw = int(text_w(text, f))
    icon = 44
    w, h = tw + 64 + icon + 14, 72
    im = rrect(w, h, 36, c + (255,))
    d = ImageDraw.Draw(im)
    if color == "red":
        tri = Image.new("RGBA", (icon * SS, icon * SS), (0, 0, 0, 0))
        td = ImageDraw.Draw(tri)
        s = icon * SS
        td.polygon([(s / 2, s * 0.08), (s * 0.96, s * 0.9), (s * 0.04, s * 0.9)], fill=WHITE)
        td.text((s / 2, s * 0.62), "!", font=font("Black", int(s * 0.55)), fill=c, anchor="mm")
        im.alpha_composite(tri.resize((icon, icon), Image.LANCZOS), (30, (h - icon) // 2 - 2))
    else:
        im.alpha_composite(check_icon(icon, WHITE + (255,), c), (28, (h - icon) // 2))
    d.text((30 + icon + 14, h // 2 + 1), text, font=f, fill=WHITE, anchor="lm")
    return with_shadow(im, blur=16, offset=(0, 10), alpha=0.5, pad=40)


def logo_card(w=860, sub="LAWRENCE & THE TEAM", pad=60):
    logo = Image.open(os.path.join(ROOT, "assets", "logo", "fenland_logo.png")).convert("RGBA")
    lw = w - 2 * pad
    lh = round(logo.height * lw / logo.width)  # uniform scale: no distortion
    logo = logo.resize((lw, lh), Image.LANCZOS)
    h = lh + 2 * pad + (50 if sub else 0)
    card = rrect(w, h, 30, (255, 255, 255, 255))
    card.alpha_composite(logo, (pad, pad - 5))
    if sub:
        d = ImageDraw.Draw(card)
        d.text((w // 2, 55 + lh + 52), sub, font=font("Bold", 30), fill=GREY, anchor="mm")
    return with_shadow(card)


def map_card():
    w, h = 900, 300
    card = rrect(w, h, 28, CREAM)
    mw = 250
    mp = Image.new("RGBA", (mw * SS, mw * SS), (214, 222, 228, 255))
    d = ImageDraw.Draw(mp)
    rnd = random.Random(3)
    for i in range(7):
        x = rnd.randint(0, mw * SS)
        d.line([(x, 0), (x + rnd.randint(-200, 200), mw * SS)], fill=(250, 250, 250), width=14)
        y = rnd.randint(0, mw * SS)
        d.line([(0, y), (mw * SS, y + rnd.randint(-200, 200))], fill=(250, 250, 250), width=10)
    d.ellipse((60, 420, 330, 640), fill=(190, 214, 180))
    d.ellipse((470, 80, 700, 260), fill=(176, 206, 228))
    mp = mp.resize((mw, mw), Image.LANCZOS)
    m = rrect(mw, mw, 20, (255, 255, 255, 255)).split()[3]
    mpc = Image.new("RGBA", (mw, mw), (0, 0, 0, 0))
    mpc.paste(mp, (0, 0), m)
    card.alpha_composite(mpc, (25, 25))
    d = ImageDraw.Draw(card)
    d.text((306, 26), "Serving", font=font("Medium", 26), fill=GREY)
    for i, region in enumerate(("Lincolnshire", "Northern Cambridgeshire", "Western Norfolk")):
        d.text((304, 60 + i * 50), region, font=font("Bold", 38), fill=INK)
    chip = rrect(360, 46, 23, ORANGE + (255,))
    ImageDraw.Draw(chip).text((180, 24), "PE12 7LD · 30-MILE RADIUS", font=font("ExtraBold", 21),
                              fill=WHITE, anchor="mm")
    card.alpha_composite(chip, (306, 226))
    return card, (25, 25, mw)


def pin_overlay(size, t):
    """Pulsing radius rings + pin, drawn per frame into map area."""
    im = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = size * SS / 2
    for k in range(2):
        ph = ((t * 0.9) + k * 0.5) % 1.0
        r = (0.12 + 0.36 * ph) * size * SS
        a = int(200 * (1 - ph))
        d.ellipse((c - r, c - r, c + r, c + r), outline=ORANGE + (a,), width=3 * SS)
    r0 = 0.4 * size * SS
    d.ellipse((c - r0, c - r0, c + r0, c + r0), outline=ORANGE + (120,), width=2 * SS)
    # pin
    pw = size * SS * 0.16
    py = c - pw * 0.9
    d.ellipse((c - pw / 2, py - pw / 2, c + pw / 2, py + pw / 2), fill=ORANGE)
    d.polygon([(c - pw * 0.42, py + pw * 0.2), (c + pw * 0.42, py + pw * 0.2), (c, c)],
              fill=ORANGE)
    d.ellipse((c - pw * 0.18, py - pw * 0.18, c + pw * 0.18, py + pw * 0.18), fill=WHITE)
    return im.resize((size, size), Image.LANCZOS)


def chip_sprite(text):
    f = font("ExtraBold", 36)
    tw = int(text_w(text, f))
    w, h = tw + 120, 82
    im = rrect(w, h, 41, CREAM)
    im.alpha_composite(check_icon(48, GREEN + (255,)), (20, (h - 48) // 2))
    ImageDraw.Draw(im).text((82, h // 2 + 1), text, font=f, fill=INK, anchor="lm")
    return with_shadow(im, blur=16, offset=(0, 10), alpha=0.5, pad=40)


def report_card(img_path, header, badge, foot):
    w = 800
    iw, ih = w - 50, 430
    card_h = 70 + ih + 120
    card = rrect(w, card_h, 30, CREAM)
    d = ImageDraw.Draw(card)
    d.text((32, 40), header, font=font("ExtraBold", 26), fill=(60, 56, 52), anchor="lm")
    b = rrect(120, 40, 20, GREEN + (255,))
    ImageDraw.Draw(b).text((60, 21), badge, font=font("ExtraBold", 22), fill=WHITE, anchor="mm")
    card.alpha_composite(b, (w - 150, 20))
    src = Image.open(img_path).convert("RGBA")
    # crop a paving close-up region from the plate keeping aspect
    sw, sh = src.size
    cw = sw
    chh = int(cw * ih / iw)
    top = int(sh * 0.48)
    crop = src.crop((0, top, cw, min(sh, top + chh))).resize((iw, ih), Image.LANCZOS)
    m = rrect(iw, ih, 20, (255, 255, 255, 255)).split()[3]
    pic = Image.new("RGBA", (iw, ih), (0, 0, 0, 0))
    pic.paste(crop, (0, 0), m)
    card.alpha_composite(pic, (25, 70))
    fw = 560
    fp = rrect(fw, 64, 32, ORANGE + (255,))
    fp.alpha_composite(check_icon(40, WHITE + (255,), ORANGE), (16, 12))
    ImageDraw.Draw(fp).text((fw // 2 + 22, 33), foot, font=font("Bold", 28), fill=WHITE,
                            anchor="mm")
    card.alpha_composite(fp, ((w - fw) // 2, 70 + ih + 28))
    return card, (25, 70, iw, ih)


def report_marks(iw, ih, prog):
    """Orange annotation circles drawn on (arc draw-on)."""
    im = Image.new("RGBA", (iw * SS, ih * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for k, (cx, cy, r) in enumerate(((0.32, 0.5, 0.16), (0.68, 0.56, 0.16))):
        p = clamp(prog * 2 - k * 0.6)
        if p <= 0:
            continue
        box = ((cx - r * ih / iw) * iw * SS, (cy - r) * ih * SS,
               (cx + r * ih / iw) * iw * SS, (cy + r) * ih * SS)
        d.arc(box, -90, -90 + 360 * p, fill=ORANGE + (255,), width=7 * SS)
    return im.resize((iw, ih), Image.LANCZOS)


def cta_button(text, w=780, h=124):
    im = rrect(w, h, h // 2, GREEN + (255,))
    f = font("ExtraBold", 46)
    tw = text_w(text, f)
    icon = 52
    x0 = (w - tw - icon - 18) / 2
    im.alpha_composite(phone_icon(icon), (int(x0), (h - icon) // 2))
    ImageDraw.Draw(im).text((x0 + icon + 18, h // 2 + 2), text, font=f, fill=WHITE,
                            anchor="lm")
    return with_shadow(im, blur=24, offset=(0, 12), alpha=0.6, pad=50)


# ---------------------------------------------------------------- particles
def soft_dot(d, color, blur):
    pad = blur * 3
    im = Image.new("RGBA", (d + 2 * pad, d + 2 * pad), (0, 0, 0, 0))
    ImageDraw.Draw(im).ellipse((pad, pad, pad + d, pad + d), fill=color)
    return im.filter(ImageFilter.GaussianBlur(blur))


def star_sprite(size, color=(255, 214, 120)):
    s = size * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = s / 2
    pts = []
    for i in range(8):
        r = c if i % 2 == 0 else c * 0.28
        a = math.pi / 4 * i - math.pi / 2
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=color + (255,))
    im = im.resize((size, size), Image.LANCZOS)
    g = im.filter(ImageFilter.GaussianBlur(size / 5))
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.alpha_composite(g)
    out.alpha_composite(g)
    out.alpha_composite(im)
    return out


class Particles:
    def __init__(self):
        rnd = random.Random(11)
        self.rain = [(rnd.uniform(-100, W + 100), rnd.uniform(0, H), rnd.uniform(38, 62),
                      rnd.uniform(40, 90), rnd.uniform(0.25, 0.6)) for _ in range(150)]
        self.bokeh_sprites = [soft_dot(d, (255, 190, 110, 255), b) for d, b in
                              ((10, 2), (18, 4), (30, 8), (46, 12))]
        self.bokeh = [(rnd.uniform(0, W), rnd.uniform(0, H), rnd.randrange(4),
                       rnd.uniform(-0.4, 0.4), rnd.uniform(-1.2, -0.3), rnd.uniform(0, 6.28),
                       rnd.uniform(0.15, 0.55)) for _ in range(40)]
        self.stars = [star_sprite(s) for s in (18, 28, 44, 70)]
        self.sparks = [(rnd.uniform(60, W - 60), rnd.uniform(380, 1250), rnd.randrange(3),
                        rnd.uniform(0, 6.28), rnd.uniform(1.5, 3.5)) for _ in range(28)]

    def draw_rain(self, img, f, strength=1.0):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        for x0, y0, v, L, a in self.rain:
            y = (y0 + v * f) % (H + 200) - 100
            x = x0 - 0.18 * (y - y0)
            x = x % (W + 200) - 100
            d.line([(x, y), (x - 0.18 * L, y + L)], fill=(200, 215, 255, int(110 * a * strength)),
                   width=2)
        img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(0.6)))

    def draw_bokeh(self, img, f, strength=1.0):
        for x0, y0, k, vx, vy, ph, a in self.bokeh:
            x = (x0 + vx * f) % W
            y = (y0 + vy * f) % H
            tw = 0.6 + 0.4 * math.sin(ph + f * 0.07)
            sp = self.bokeh_sprites[k]
            alpha = a * tw * strength
            if alpha <= 0.02:
                continue
            s = sp.copy()
            s.putalpha(s.split()[3].point(lambda v, al=alpha: int(v * al)))
            img.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))

    def draw_sparkles(self, img, f, t_local, cx=540, cy=760):
        for x, y, k, ph, sp in self.sparks:
            tw = 0.5 + 0.5 * math.sin(ph + f * 0.12 * sp)
            if tw < 0.15:
                continue
            s = self.stars[k].copy()
            sc = 0.5 + 0.5 * tw
            s = s.resize((max(2, int(s.width * sc)), max(2, int(s.height * sc))), Image.LANCZOS)
            s.putalpha(s.split()[3].point(lambda v, al=tw: int(v * al)))
            img.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))
        # swirl trail orbiting the mascot (reference: sparkle trail + star)
        ang0 = t_local * 2.4
        for i in range(26):
            a = ang0 - i * 0.12
            r = 360 - i * 2
            x = cx + r * math.cos(a)
            y = cy + r * 0.55 * math.sin(a)
            al = (1 - i / 26) ** 1.5
            s = self.stars[0 if i else 2].copy()
            s.putalpha(s.split()[3].point(lambda v, al=al: int(v * al)))
            img.alpha_composite(s, (int(x - s.width / 2), int(y - s.height / 2)))


# ---------------------------------------------------------------- captions
def layout_chunk(chunk):
    f = font("Bold", CAP_SIZE)
    space = text_w(" ", f)
    lines, cur, cw = [], [], 0
    for wd in chunk["words"]:
        ww = text_w(wd["text"], f)
        if cur and cw + space + ww > CAP_MAXW:
            lines.append(cur)
            cur, cw = [], 0
        cur.append((wd, ww))
        cw += (space if len(cur) > 1 else 0) + ww
    lines.append(cur)
    placed = []
    for li, line in enumerate(lines):
        x = CAP_X
        for wd, ww in line:
            placed.append((wd, x, CAP_Y + li * CAP_LH, ww))
            x += ww + space
    return placed


CHUNK_LAYOUT = [layout_chunk(c) for c in TL["captions"]]


def draw_captions(img, t):
    ci = None
    for i, c in enumerate(TL["captions"]):
        if c["start"] - 0.02 <= t < c["end"] - 0.02:
            ci = i
    if ci is None:
        return
    c = TL["captions"][ci]
    out_fade = clamp((c["end"] - 0.02 - t) / 0.08)  # quick out
    layer = Image.new("RGBA", (W, 420), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font("Bold", CAP_SIZE)
    for wd, x, y, ww in CHUNK_LAYOUT[ci]:
        st = wd["s"] - 0.03
        if t < st:
            continue
        p = ease_out((t - st) / 0.12)
        a = int(255 * p * out_fade)
        dy = (1 - p) * 14
        col = ORANGE if wd["hl"] else WHITE
        d.text((x, y + dy), wd["text"], font=f, fill=col + (a,))
        if wd["hl"]:
            up = ease_out((t - st - 0.06) / 0.18)
            if up > 0:
                tw = text_w(wd["text"].rstrip(",.?!"), f) if len(wd["text"]) > 1 else ww
                uy = y + CAP_SIZE + 12 + dy
                d.rounded_rectangle((x, uy, x + max(6, tw * up), uy + 7), 3,
                                    fill=ORANGE + (a,))
    sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    sh.putalpha(layer.split()[3].point(lambda v: int(v * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(10))
    img.alpha_composite(sh, (0, 4))
    img.alpha_composite(layer, (0, 0))


# ---------------------------------------------------------------- card logic
class Cards:
    def __init__(self):
        self.cache = {}
        self.map_card = map_card()
        self.logo = logo_card()
        self.logo_cta = logo_card(620, sub=None, pad=36)
        self.button = None

    def sprite(self, key, fn):
        if key not in self.cache:
            self.cache[key] = fn()
        return self.cache[key]

    @staticmethod
    def entrance(t, t0, dur=0.32):
        p = ease_out((t - t0) / dur)
        return p

    def put(self, img, spr_pad, x, y, p, t, phase=0.0, hover=5, scale_in=True):
        spr, pad = spr_pad
        if p <= 0:
            return
        bob = math.sin(t * 2.2 + phase) * hover
        sc = (0.94 + 0.06 * p) if scale_in else 1.0
        s = spr
        if abs(sc - 1) > 0.003:
            s = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.BILINEAR)
        if p < 1:
            s = s.copy()
            s.putalpha(s.split()[3].point(lambda v, pp=p: int(v * pp)))
        dx = (spr.width - s.width) / 2
        dy = (spr.height - s.height) / 2 + (1 - p) * 46 + bob
        img.alpha_composite(s, (int(x - pad + dx), int(y - pad + dy)))

    def draw(self, img, t):
        for ci, c in enumerate(TL["cards"]):
            if not (c["start"] - 0.01 <= t < c["end"]):
                continue
            out = clamp((c["end"] - t) / 0.12) if c["kind"] != "cta" else 1.0
            k = c["kind"]
            if k == "tag":
                spr = self.sprite(("tag", ci), lambda: tag_sprite(c["text"], c["color"]))
                y = CARD_Y if ci != 0 else CARD_Y
                if c["text"] == "BUILT ON TRUST":
                    y = CARD_Y + 395
                if c["text"].startswith("TRANSFORM"):
                    y = CARD_Y
                self.put(img, spr, CAP_X, y, self.entrance(t, c["start"]) * out, t, ci)
            elif k == "stack":
                base = CARD_Y + (100 if ci == 1 else 0)
                if c["items"][0]["title"].startswith("Complete"):
                    base = CARD_Y + 100
                for i, it in enumerate(c["items"]):
                    spr = self.sprite(("st", ci, i), lambda it=it: card_item(
                        it["title"], it["sub"], it["num"], it["accent"], c.get("check", False)))
                    p = self.entrance(t, it["t"]) * out
                    self.put(img, spr, 90, base + i * 158, p, t, i * 1.3)
            elif k == "map":
                card, (mx, my, mw) = self.map_card
                p = self.entrance(t, c["start"]) * out
                spr = card.copy()
                spr.alpha_composite(pin_overlay(mw, t - c["start"]), (mx, my))
                self.put(img, with_shadow(spr), 90, CARD_Y + 10, p, t, 0.5)
            elif k == "logo":
                p = self.entrance(t, c["start"], 0.4) * out
                self.put(img, self.logo, (W - self.logo[0].width + 2 * self.logo[1]) // 2,
                         CARD_Y + 10, p, t, 0.3, hover=4)
            elif k == "chips":
                for i, it in enumerate(c["items"]):
                    spr = self.sprite(("chip", ci, i), lambda it=it: chip_sprite(it["text"]))
                    p = self.entrance(t, it["t"]) * out
                    self.put(img, spr, CAP_X + 10, CARD_Y + i * 104, p, t, i * 1.1)
            elif k == "report":
                key = ("report", ci)
                if key not in self.cache:
                    path = os.path.join(FRAMES_DIR, c["image"], "0070.png")
                    if not os.path.exists(path):
                        continue
                    self.cache[key] = report_card(path, c["header"], c["badge"], c["foot"])
                card, (ix, iy, iw, ih) = self.cache[key]
                p = self.entrance(t, c["start"], 0.4) * out
                spr = card.copy()
                spr.alpha_composite(report_marks(iw, ih, (t - c["start"] - 0.5) / 1.0),
                                    (ix, iy))
                self.put(img, with_shadow(spr), (W - card.width) // 2, CARD_Y + 20, p, t, 0.2,
                         hover=4)
            elif k == "cta":
                self.draw_cta(img, t, c)

    def draw_cta(self, img, t, c):
        # small line, logo card, green button, contact details (all in safe zone)
        p_sub = self.entrance(t, c["sub_t"])
        if p_sub > 0:
            layer = Image.new("RGBA", (W, 60), (0, 0, 0, 0))
            ImageDraw.Draw(layer).text((W // 2, 30), c["sub"], font=font("Bold", 30),
                                       fill=WHITE + (int(235 * p_sub),), anchor="mm")
            img.alpha_composite(layer, (0, int(1040 + (1 - p_sub) * 20)))
        p_logo = self.entrance(t, c["logo_t"], 0.45)
        lg, pad = self.logo_cta
        self.put(img, self.logo_cta, (W - lg.width + 2 * pad) // 2, 1100, p_logo, t, 0.0,
                 hover=3)
        if self.button is None:
            self.button = cta_button(c["button"])
        pb = ease_out_back((t - c["button_t"]) / 0.4) if t >= c["button_t"] else 0
        if pb > 0:
            spr, pad = self.button
            pulse = 1 + 0.025 * math.sin((t - c["button_t"]) * 5.0)
            sc = max(0.05, pb * pulse)
            s = spr.resize((int(spr.width * sc), int(spr.height * sc)), Image.BILINEAR)
            a = clamp(pb)
            if a < 1:
                s.putalpha(s.split()[3].point(lambda v: int(v * a)))
            img.alpha_composite(s, (int(W / 2 - s.width / 2), int(1408 - s.height / 2)))
        pc = self.entrance(t, c["contact_t"])
        if pc > 0:
            layer = Image.new("RGBA", (W, 140), (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            d.text((W // 2, 40), c["phone"], font=font("ExtraBold", 50),
                   fill=WHITE + (int(255 * pc),), anchor="mm")
            d.text((W // 2, 100), c["web"], font=font("SemiBold", 34),
                   fill=(225, 225, 230, int(255 * pc)), anchor="mm")
            sh = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            sh.putalpha(layer.split()[3].point(lambda v: int(v * 0.6)))
            img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8)), (0, 1490 + 4))
            img.alpha_composite(layer, (0, int(1490 + (1 - pc) * 20)))


# ---------------------------------------------------------------- plates & grade
_vig = None
_grain = None


def vignette():
    global _vig
    if _vig is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.52) / (H * 0.62)) ** 2)
        _vig = np.clip(1.0 - 0.42 * np.clip(r - 0.45, 0, 1) ** 1.6, 0, 1)[..., None]
    return _vig


def grain(f):
    global _grain
    if _grain is None:
        rs = np.random.RandomState(1)
        _grain = [rs.normal(0, 3.2, (H, W, 1)).astype(np.float32) for _ in range(6)]
    return _grain[f % 6]


def shot_at(f):
    for s in TL["shots"]:
        if s["frame_start"] <= f < s["frame_start"] + s["frames"]:
            return s
    return TL["shots"][-1]


def load_plate(shot, local):
    local = max(1, min(shot["frames"], local))
    p = os.path.join(FRAMES_DIR, shot["name"], f"{local:04d}.png")
    if not os.path.exists(p):
        # tolerate missing frames during development: nearest existing
        d = os.path.join(FRAMES_DIR, shot["name"])
        have = sorted(int(x[:4]) for x in os.listdir(d)) if os.path.isdir(d) else []
        if not have:
            return Image.new("RGB", (W, H), (8, 10, 20))
        local = min(have, key=lambda v: abs(v - local))
        p = os.path.join(d, f"{local:04d}.png")
    im = Image.open(p).convert("RGB")
    if im.size != (W, H):
        im = im.resize((W, H), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    return im


PARTS = None
CARDS = None


def scene_layer(f):
    """3D plate + particles + cards for global frame f (0-based)."""
    t = f / FPS
    shot = shot_at(f)
    local = f - shot["frame_start"] + 1
    img = load_plate(shot, local).convert("RGBA")
    n = shot["name"]
    if n in ("s1_exterior", "s2_worry"):
        PARTS.draw_rain(img, f)
    elif n == "s9_cta":
        PARTS.draw_bokeh(img, f, 0.8)
        PARTS.draw_sparkles(img, f, t - shot["start"])
    elif n not in ("s3_region",):
        PARTS.draw_bokeh(img, f, 0.35)
    CARDS.draw(img, t)
    arr = np.asarray(img.convert("RGB")).astype(np.float32)
    arr = arr * vignette() + grain(f)
    return np.clip(arr, 0, 255)


def hblur(arr, L, axis=1):
    L = int(L)
    if L < 2:
        return arr
    c = np.cumsum(np.pad(arr, [(L, L) if a == axis else (0, 0) for a in range(3)],
                         mode="edge"), axis=axis)
    if axis == 1:
        out = (c[:, L:-L] - c[:, :-2 * L]) / L
    else:
        out = (c[L:-L] - c[:-2 * L]) / L
    return out[:H, :W] if out.shape[0] >= H else out


def transition(arr, kind, k):
    """k: 0..1 transition intensity; sign of motion handled by caller."""
    if kind.startswith("whip"):
        axis = 0 if kind == "whip_up" else 1
        L = 4 + 260 * k
        shift = int(300 * k * k)
        out = hblur(arr, L, axis)
        out = np.roll(out, -shift if axis == 1 else -shift, axis=axis)
        return out
    if kind == "zoom":
        img = Image.fromarray(arr.astype(np.uint8))
        acc = arr.copy()
        for i in range(1, 5):
            sc = 1 + 0.06 * k * i
            z = img.resize((int(W * sc), int(H * sc)), Image.BILINEAR)
            x0, y0 = (z.width - W) // 2, (z.height - H) // 2
            acc += np.asarray(z.crop((x0, y0, x0 + W, y0 + H))).astype(np.float32)
        return acc / 5
    if kind == "blur":
        img = Image.fromarray(arr.astype(np.uint8)).filter(ImageFilter.GaussianBlur(28 * k))
        return np.asarray(img).astype(np.float32)
    return arr


CUTS = {s["frame_start"]: s for s in TL["shots"][1:]}
PREV = {TL["shots"][i + 1]["frame_start"]: TL["shots"][i] for i in range(len(TL["shots"]) - 1)}
HALF = 4  # frames each side of a cut


def frame(f):
    t = f / FPS
    arr = None
    for c, nxt in CUTS.items():
        prev = PREV[c]
        kind = prev.get("transition_out") or "whip_left"
        if c - HALF <= f < c:  # outgoing
            k = (f - (c - HALF) + 1) / HALF
            arr = transition(scene_layer(f), kind, k)
            if kind == "blur":
                pass
            elif kind.startswith("whip"):
                pass
        elif c <= f < c + HALF:  # incoming
            k = 1 - (f - c) / HALF
            base = scene_layer(f)
            if kind.startswith("whip"):
                axis = 0 if kind == "whip_up" else 1
                L = 4 + 260 * k
                shift = int(300 * k * k)
                out = hblur(base, L, axis)
                arr = np.roll(out, shift, axis=axis)
            elif kind == "blur":
                last = scene_layer(c - 1)
                a = transition(last, "blur", 1.0)
                b = transition(base, "blur", k)
                mix = 1 - k
                arr = a * (1 - mix) + b * mix
            else:
                arr = transition(base, kind, k)
    if arr is None:
        arr = scene_layer(f)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    draw_captions(img, t)
    return img.convert("RGB")


def main():
    global PARTS, CARDS
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", default="")
    ap.add_argument("--out", default=os.path.join(ROOT, "build", "video_noaudio.mp4"))
    ap.add_argument("--range", default="")
    a = ap.parse_args()
    PARTS = Particles()
    CARDS = Cards()
    total = TL["total_frames"]
    if a.frames:
        os.makedirs(os.path.join(ROOT, "build", "stills"), exist_ok=True)
        for f in [int(x) for x in a.frames.split(",")]:
            frame(f).save(os.path.join(ROOT, "build", "stills", f"{f:04d}.png"))
            print("still", f, flush=True)
        return
    r0, r1 = (map(int, a.range.split(":")) if a.range else (0, total))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "slow",
           "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in range(r0, r1):
        proc.stdin.write(frame(f).tobytes())
        if f % 30 == 0:
            print("frame", f, flush=True)
    proc.stdin.close()
    proc.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    main()
