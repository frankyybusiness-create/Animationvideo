"""Compositor: Blender renders + captions / floating UI / transitions -> final MP4.

    python src/compose/compose.py                      # full render -> output/sureshield_roofing_tiktok.mp4
    python src/compose/compose.py --stills 1.5,6,15    # PNG stills for review
    python src/compose/compose.py --placeholder ...    # missing renders -> flat backdrop (UI testing)

Motion language follows the Oct-20Footage1 reference:
  * captions top-left, Inter Bold, white; words rise in from a dim/low state,
    key words orange with a drawn-on underline; captions dim out on the cut
  * cream rounded cards with coloured accent strip, soft shadow, slight tilt;
    they resolve out of a blur, settle, and hover independently
  * whip-pan cuts with heavy horizontal motion blur; defocus dissolves into
    and out of UI panels
"""
import argparse
import functools
import json
import math
import os
import random
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TL = json.load(open(os.path.join(ROOT, "config", "timeline.json")))
OV = json.load(open(os.path.join(ROOT, "config", "overlays.json")))
FPS = TL["fps"]
W, H = TL["width"], TL["height"]
HANDLE = 6
FONT_DIR = "/usr/share/fonts/opentype/inter"

ORANGE = (247, 106, 50)
CREAM = (247, 242, 235)
INK = (27, 24, 28)
GREY = (96, 97, 100)
GREEN = (43, 208, 102)
STRIPS = [(248, 154, 68), (233, 108, 46), (247, 106, 50)]

MARGIN_X = 68
CAP_BASELINE = 222
CAP_SIZE = 80
CAP_LINE = 92


@functools.lru_cache(maxsize=None)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, name + ".otf"), size)


# ---------------------------------------------------------------------------
# easing
# ---------------------------------------------------------------------------

def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_out_back(x, s=1.6):
    x = clamp(x)
    return 1 + (s + 1) * (x - 1) ** 3 + s * (x - 1) ** 2


def lerp(a, b, x):
    return a + (b - a) * x


# ---------------------------------------------------------------------------
# 3D render access
# ---------------------------------------------------------------------------

SHOTS = TL["shots"]
PLACEHOLDER = False


@functools.lru_cache(maxsize=48)
def load_render(shot_id, f):
    d = os.path.join(ROOT, "renders", shot_id)
    p = os.path.join(d, f"{f:04d}.png")
    if os.path.exists(p):
        return np.asarray(Image.open(p).convert("RGB"), dtype=np.float32)
    # rendered on twos: blend the neighbours
    a = os.path.join(d, f"{f - 1:04d}.png")
    b = os.path.join(d, f"{f + 1:04d}.png")
    if os.path.exists(a) and os.path.exists(b):
        return (load_render(shot_id, f - 1) + load_render(shot_id, f + 1)) * 0.5
    for k in range(1, 4):
        for c in (f - k, f + k):
            q = os.path.join(d, f"{c:04d}.png")
            if os.path.exists(q):
                return load_render(shot_id, c)
    if PLACEHOLDER:
        g = np.linspace(0, 1, 960, dtype=np.float32)[:, None, None]
        img = (np.array([6, 9, 22], np.float32) * (1 - g) + np.array([40, 30, 40], np.float32) * g)
        return np.broadcast_to(img, (960, 540, 3)).copy()
    raise FileNotFoundError(p)


def shot_frame(shot, t):
    n = round((shot["end"] - shot["start"]) * FPS) + 2 * HANDLE
    f = round((t - shot["start"]) * FPS) + HANDLE + 1
    return load_render(shot["id"], int(clamp(f, 1, n)))


def hblur(img, r):
    """Horizontal box blur (motion blur) via cumulative sums."""
    r = int(r)
    if r < 1:
        return img
    pad = np.pad(img, ((0, 0), (r + 1, r), (0, 0)), mode="edge")
    c = np.cumsum(pad, axis=1)
    return (c[:, 2 * r + 1:] - c[:, :-2 * r - 1]) / (2 * r + 1)


def gblur(img, r):
    if r < 0.3:
        return img
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r)), dtype=np.float32)


TRANS_FR = 8  # transition length in frames, centred on the cut


def base_image(t):
    """Background plate at render resolution (540x960) incl. transitions."""
    idx = next((i for i, s in enumerate(SHOTS) if s["start"] <= t < s["end"]), len(SHOTS) - 1)
    half = TRANS_FR / 2 / FPS
    for i in range(1, len(SHOTS)):
        tc = SHOTS[i]["start"]
        if abs(t - tc) < half:
            A, B = SHOTS[i - 1], SHOTS[i]
            p = (t - (tc - half)) / (2 * half)
            kind = OV["transitions"].get(f"{A['id']}>{B['id']}", OV["transitions"]["default"])
            fa, fb = shot_frame(A, t), shot_frame(B, t)
            if kind == "defocus":
                bl = math.sin(math.pi * p) * 14
                m = ease_in_out(p)
                return gblur(fa, bl) * (1 - m) + gblur(fb, bl) * m
            # whip pan: A exits left, B enters from the right, heavy motion blur
            e = ease_in_out(p)
            w = fa.shape[1]
            sh = int(e * w)
            canvas = np.concatenate([fa, fb], axis=1)[:, sh:sh + w]
            return hblur(canvas, math.sin(math.pi * p) * 95)
    return shot_frame(SHOTS[idx], t)


# ---------------------------------------------------------------------------
# full-res FX: rain, sparkles, grade
# ---------------------------------------------------------------------------

def make_rain(seed, n, speed, length, alpha, width):
    rnd = random.Random(seed)
    return [dict(x=rnd.uniform(-200, W + 200), y=rnd.uniform(0, H), sp=speed * rnd.uniform(0.8, 1.2),
                 ln=length * rnd.uniform(0.7, 1.3), a=int(alpha * rnd.uniform(0.5, 1.0)), w=width)
            for _ in range(n)]


RAIN = [make_rain(1, 70, 2300, 70, 70, 2), make_rain(2, 120, 1400, 34, 45, 1)]


def draw_rain(layer, t):
    d = ImageDraw.Draw(layer)
    for streaks in RAIN:
        for s in streaks:
            y = (s["y"] + s["sp"] * t) % (H + 200) - 100
            x = s["x"] - 0.12 * (s["sp"] * t % (H + 200))
            x = x % (W + 400) - 200
            d.line([(x, y), (x - 0.12 * s["ln"], y - s["ln"])], fill=(205, 218, 255, s["a"]), width=s["w"])


def _glow_sprite(r, color):
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    d = np.sqrt(xx ** 2 + yy ** 2) / r
    a = np.clip(1 - d, 0, 1) ** 2.2
    core = np.clip(1 - d * 3.5, 0, 1)
    rgb = np.array(color, np.float32)[None, None] * a[..., None] + 255 * core[..., None]
    return rgb


SPARK = _glow_sprite(14, (255, 196, 92))
_rs = random.Random(7)
SPARKS = [dict(cx=_rs.uniform(0, W), cy=_rs.uniform(250, 1500), r=_rs.uniform(30, 170), ph=_rs.uniform(0, 6.28),
               sp=_rs.uniform(0.15, 0.6), tw=_rs.uniform(1.5, 4), s=_rs.uniform(0.3, 1.0)) for _ in range(120)]


def add_sparkles(img, t, t0):
    k = ease_out((t - t0) / 0.8)
    if k <= 0:
        return img
    for p in SPARKS:
        a = p["ph"] + p["sp"] * (t - t0) * 2
        x = int(p["cx"] + math.cos(a) * p["r"])
        y = int(p["cy"] + math.sin(a) * p["r"] * 0.6 - (t - t0) * 25 * p["sp"])
        tw = (0.5 + 0.5 * math.sin(p["tw"] * t * 3 + p["ph"])) * p["s"] * k
        sz = SPARK.shape[0]
        x0, y0 = x - sz // 2, y - sz // 2
        if x0 < 0 or y0 < 0 or x0 + sz > W or y0 + sz > H:
            continue
        img[y0:y0 + sz, x0:x0 + sz] += SPARK * tw
    return img


_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIGNETTE = (1 - 0.32 * np.clip(((_xx / W - 0.5) ** 2 * 1.4 + (_yy / H - 0.48) ** 2) * 2.2, 0, 1) ** 1.4)[..., None]
del _yy, _xx
_rg = np.random.default_rng(3)
GRAIN = [_rg.normal(0, 3.2, (H // 2, W // 2, 1)).astype(np.float32) for _ in range(6)]


def grade(img, i):
    img = img * VIGNETTE
    g = GRAIN[i % len(GRAIN)]
    img += np.repeat(np.repeat(g, 2, 0), 2, 1)
    return img


# ---------------------------------------------------------------------------
# UI primitives
# ---------------------------------------------------------------------------

SS = 2  # supersampling for anti-aliased shapes


def rounded_card(w, h, r, fill, strip=None, strip_w=14):
    base = Image.new("RGBA", (w * SS, h * SS), (*fill, 255))
    if strip:
        ImageDraw.Draw(base).rectangle([0, 0, strip_w * SS, h * SS], fill=strip)
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w * SS - 1, h * SS - 1], r * SS, fill=255)
    base.putalpha(mask)
    return base.resize((w, h), Image.LANCZOS)


def text_tracked(d, xy, text, fnt, fill, tracking=0, anchor="ls"):
    x, y = xy
    if tracking == 0:
        d.text((x, y), text, font=fnt, fill=fill, anchor=anchor)
        return
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill, anchor=anchor)
        x += fnt.getlength(ch) + tracking


def tracked_len(text, fnt, tracking):
    return sum(fnt.getlength(c) for c in text) + tracking * (len(text) - 1)


def shadow_of(im, blur=18, alpha=0.45, grow=0):
    a = im.getchannel("A").point(lambda v: int(v * alpha))
    pad = blur * 3
    sh = Image.new("RGBA", (im.width + 2 * pad, im.height + 2 * pad), (0, 0, 0, 0))
    blk = Image.new("RGBA", im.size, (4, 6, 14, 255))
    blk.putalpha(a)
    sh.paste(blk, (pad, pad))
    return sh.filter(ImageFilter.GaussianBlur(blur)), pad


def place(layer, im, cx, cy, scale=1.0, alpha=1.0, blur=0.0, rot=0.0, darken=0.0, shadow=None):
    """Paste RGBA `im` centred at (cx, cy) with transforms."""
    if alpha <= 0.003:
        return
    if scale != 1.0:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if darken > 0:
        rgb = Image.eval(im.convert("RGB"), lambda v: int(v * (1 - darken)))
        rgb.putalpha(im.getchannel("A"))
        im = rgb
    if rot:
        im = im.rotate(rot, Image.BICUBIC, expand=True)
    if shadow:
        sh, pad = shadow_of(im, *shadow)
        sa = sh.getchannel("A").point(lambda v: int(v * alpha))
        sh.putalpha(sa)
        layer.alpha_composite(sh, (int(cx - sh.width / 2), int(cy - sh.height / 2 + 14 * scale)))
    if blur > 0.3:
        padb = int(blur * 3)
        big = Image.new("RGBA", (im.width + 2 * padb, im.height + 2 * padb), (0, 0, 0, 0))
        big.paste(im, (padb, padb))
        im = big.filter(ImageFilter.GaussianBlur(blur))
    if alpha < 1:
        im = im.copy()
        im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    layer.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))


def check_icon(size, color, bg=None, stroke=None):
    s = size * SS
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if bg:
        d.ellipse([0, 0, s - 1, s - 1], fill=bg)
    w = stroke or max(2, int(s * 0.12))
    d.line([(s * 0.27, s * 0.52), (s * 0.44, s * 0.68), (s * 0.74, s * 0.34)], fill=color, width=w, joint="curve")
    return im.resize((size, size), Image.LANCZOS)


# ---------------------------------------------------------------------------
# captions
# ---------------------------------------------------------------------------

class Caption:
    def __init__(self, spec):
        self.out = spec["out"]
        self.words = []
        f = font("Inter-Bold", CAP_SIZE)
        space = f.getlength(" ")
        x, line = MARGIN_X, 0
        for text, t_in, hl in spec["words"]:
            if text == "\n":
                x, line = MARGIN_X, line + 1
                continue
            w = f.getlength(text)
            if x + w > W - MARGIN_X and x > MARGIN_X:
                x, line = MARGIN_X, line + 1
            self.words.append(dict(text=text, t=t_in, hl=hl, x=x, y=CAP_BASELINE + line * CAP_LINE, w=w))
            x += w + space
        self.t0 = min(w["t"] for w in self.words)

    def active(self, t):
        return self.t0 - 0.05 <= t < self.out + 0.25

    def draw(self, layer, t):
        f = font("Inter-Bold", CAP_SIZE)
        txt = Image.new("RGBA", (W, 520), (0, 0, 0, 0))
        d = ImageDraw.Draw(txt)
        fade = 1 - ease_out((t - self.out) / 0.22)
        for wd in self.words:
            p = (t - wd["t"]) / 0.24
            if p <= 0:
                continue
            e = ease_out(p)
            a = lerp(0.3, 1.0, e) * fade
            dy = lerp(16, 0, e)
            base = (255, 255, 255)
            if wd["hl"]:
                k = ease_out((t - wd["t"] - 0.05) / 0.2)
                base = tuple(int(lerp(c1, c2, k)) for c1, c2 in zip((255, 255, 255), ORANGE))
            grey = (150, 150, 155)
            col = tuple(int(lerp(g, c, e)) for g, c in zip(grey, base))
            d.text((wd["x"], wd["y"] + dy), wd["text"], font=f, fill=(*col, int(255 * a)), anchor="ls")
            if wd["hl"]:
                u = ease_out((t - wd["t"] - 0.12) / 0.25)
                if u > 0:
                    x0 = wd["x"]
                    x1 = x0 + wd["w"] * u
                    yb = wd["y"] + 16
                    d.rounded_rectangle([x0, yb, max(x0 + 7, x1), yb + 7], 3, fill=(*ORANGE, int(255 * a)))
        sh = txt.getchannel("A").point(lambda v: int(v * 0.5)).filter(ImageFilter.GaussianBlur(6))
        shadow = Image.new("RGBA", txt.size, (0, 0, 0, 0))
        shadow.putalpha(sh)
        layer.alpha_composite(shadow, (0, 4))
        layer.alpha_composite(txt, (0, 0))


CAPTIONS = [Caption(c) for c in OV["captions"]]


# ---------------------------------------------------------------------------
# floating cards
# ---------------------------------------------------------------------------

def benefit_card(i, title, sub):
    w, h = 900, 150
    card = rounded_card(w, h, 26, CREAM, strip=STRIPS[i])
    d = ImageDraw.Draw(card)
    badge = check_icon(62, ORANGE, bg=(236, 230, 222), stroke=10)
    card.alpha_composite(badge, (44, (h - 62) // 2))
    d.text((132, 82), title, font=font("Inter-ExtraBold", 52), fill=INK, anchor="ls")
    d.text((133, 124), sub, font=font("Inter-Medium", 32), fill=GREY, anchor="ls")
    return card


@functools.lru_cache(maxsize=None)
def cards_imgs():
    return [benefit_card(i, c["title"], c["sub"]) for i, c in enumerate(OV["benefit_cards"]["cards"])]


CARD_Y = [440, 612, 784]
CARD_ROT = [0.9, -0.6, 0.7]


def entrance(t, t_in, dur=0.38):
    p = (t - t_in) / dur
    return clamp(p), ease_out(p), ease_out_back(p, 1.3)


def draw_benefit_cards(layer, t):
    bc = OV["benefit_cards"]
    out_k = 1 - ease_out((t - bc["out"]) / 0.22)
    if out_k <= 0:
        return
    for i, (c, im) in enumerate(zip(bc["cards"], cards_imgs())):
        p, e, eb = entrance(t, c["in"])
        if p <= 0:
            continue
        hover = 5 * math.sin(2 * math.pi * 0.42 * t + i * 1.9)
        cy = CARD_Y[i] + lerp(70, 0, eb) + hover
        place(layer, im, W / 2, cy, scale=lerp(0.94, 1.0, e), alpha=e * out_k, blur=lerp(12, 0, e) + (1 - out_k) * 8,
              rot=CARD_ROT[i] + lerp(3 * (1 if i % 2 else -1), 0, e), darken=lerp(0.45, 0, e),
              shadow=(18, 0.55))


@functools.lru_cache(maxsize=None)
def name_card_img():
    nc = OV["name_card"]
    w, h = 900, 214
    card = rounded_card(w, h, 30, CREAM, strip=ORANGE, strip_w=16)
    d = ImageDraw.Draw(card)
    f1 = font("Inter-ExtraBold", 96)
    f2 = font("Inter-Bold", 40)
    l1 = tracked_len(nc["line1"], f1, 2)
    l2 = tracked_len(nc["line2"], f2, 9)
    text_tracked(d, ((w - l1) / 2 + 8, 118), nc["line1"], f1, INK, 2)
    text_tracked(d, ((w - l2) / 2 + 8, 176), nc["line2"], f2, ORANGE, 9)
    return card


def draw_name_card(layer, t):
    nc = OV["name_card"]
    p, e, eb = entrance(t, nc["in"], 0.45)
    out_k = 1 - ease_out((t - nc["out"]) / 0.22)
    if p <= 0 or out_k <= 0:
        return
    hover = 5 * math.sin(2 * math.pi * 0.35 * t)
    place(layer, name_card_img(), W / 2, 470 + lerp(80, 0, eb) + hover, scale=lerp(0.9, 1, e), alpha=e * out_k,
          blur=lerp(14, 0, e) + (1 - out_k) * 8, rot=lerp(-3, -0.6, e), darken=lerp(0.4, 0, e), shadow=(20, 0.55))


# ---------------------------------------------------------------------------
# inspection panel
# ---------------------------------------------------------------------------

PANEL = dict(w=920, h=900, img_w=876, img_h=600, img_y=104)


@functools.lru_cache(maxsize=None)
def panel_base():
    ip = OV["inspection_panel"]
    w, h = PANEL["w"], PANEL["h"]
    card = rounded_card(w, h, 40, CREAM)
    d = ImageDraw.Draw(card)
    text_tracked(d, (34, 72), ip["header"], font("Inter-Bold", 36), INK, 5)
    pf = font("Inter-ExtraBold", 30)
    pw = pf.getlength(ip["pill"]) + 48
    pill = rounded_card(int(pw), 54, 27, ORANGE)
    ImageDraw.Draw(pill).text((pw / 2, 38), ip["pill"], font=pf, fill=(255, 255, 255), anchor="ms")
    card.alpha_composite(pill, (int(w - 26 - pw), 26))
    src = Image.open(os.path.join(ROOT, ip["image"])).convert("RGB")
    iw, ih = PANEL["img_w"], PANEL["img_h"]
    sc = max(iw / src.width, ih / src.height)
    src = src.resize((int(src.width * sc + 0.5), int(src.height * sc + 0.5)), Image.LANCZOS)
    ox, oy = (src.width - iw) // 2, (src.height - ih) // 2
    src = src.crop((ox, oy, ox + iw, oy + ih))
    mask = Image.new("L", (iw * SS, ih * SS), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, iw * SS - 1, ih * SS - 1], 26 * SS, fill=255)
    card.paste(src, ((w - iw) // 2, PANEL["img_y"]), mask.resize((iw, ih), Image.LANCZOS))
    return card


@functools.lru_cache(maxsize=None)
def badge_img(text):
    f = font("Inter-ExtraBold", 38)
    w = int(f.getlength(text) + 120)
    b = rounded_card(w, 76, 20, ORANGE)
    b.alpha_composite(check_icon(40, ORANGE, bg=(255, 255, 255), stroke=8), (24, 18))
    ImageDraw.Draw(b).text((80, 52), text, font=f, fill=(255, 255, 255), anchor="ls")
    return b


def draw_panel(layer, t):
    ip = OV["inspection_panel"]
    p, e, eb = entrance(t, ip["in"], 0.45)
    out_k = 1 - ease_out((t - ip["out"]) / 0.2)
    if p <= 0 or out_k <= 0:
        return
    card = panel_base().copy()
    d = ImageDraw.Draw(card)
    ix0 = (PANEL["w"] - PANEL["img_w"]) // 2
    for cx, cy, r, t_c in ip["circles"]:
        k = ease_in_out((t - t_c) / 0.35)
        if k <= 0:
            continue
        R = r * PANEL["img_w"]
        X = ix0 + cx * PANEL["img_w"]
        Y = PANEL["img_y"] + cy * PANEL["img_h"]
        d.arc([X - R, Y - R * 0.95, X + R, Y + R * 0.95], -100, -100 + 360 * k, fill=ORANGE, width=9)
    b = ip["badge"]
    pb, eb2, ebb = entrance(t, b["in"], 0.35)
    if pb > 0:
        bi = badge_img(b["text"])
        place(card, bi, PANEL["w"] / 2, 800 + lerp(20, 0, ebb), scale=lerp(0.7, 1, ebb), alpha=eb2,
              rot=lerp(-6, -1.5, ebb))
    hover = 6 * math.sin(2 * math.pi * 0.4 * t)
    place(layer, card, W / 2, 960 + lerp(90, 0, eb) + hover, scale=lerp(0.93, 1, e), alpha=e * out_k,
          blur=lerp(16, 0, e) + (1 - out_k) * 10, rot=lerp(2.5, 0, e), shadow=(24, 0.6))


# ---------------------------------------------------------------------------
# CTA
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=None)
def cta_button():
    c = OV["cta"]
    w, h = 800, 124
    f = font("Inter-ExtraBold", 52)
    btn = rounded_card(w, h, 62, GREEN)
    d = ImageDraw.Draw(btn)
    tw = f.getlength(c["button"])
    arrow_w = 46
    x0 = (w - tw - arrow_w - 18) / 2
    d.text((x0, 84), c["button"], font=f, fill=(255, 255, 255), anchor="ls")
    ax = x0 + tw + 22
    d.line([(ax, 62), (ax + arrow_w - 6, 62)], fill=(255, 255, 255), width=8)
    d.line([(ax + arrow_w - 24, 44), (ax + arrow_w - 4, 62), (ax + arrow_w - 24, 80)], fill=(255, 255, 255),
           width=8, joint="curve")
    glow = Image.new("RGBA", (w + 160, h + 160), (0, 0, 0, 0))
    ImageDraw.Draw(glow).rounded_rectangle([80, 80, 80 + w, 80 + h], 62, fill=(*GREEN, 150))
    glow = glow.filter(ImageFilter.GaussianBlur(26))
    glow.alpha_composite(btn, (80, 80))
    return glow


@functools.lru_cache(maxsize=None)
def bottom_shade():
    g = np.clip((np.arange(H) - 1180) / 620, 0, 1) ** 1.3 * 0.82
    a = (np.repeat(g[:, None], W, 1) * 255).astype(np.uint8)
    im = Image.new("RGBA", (W, H), (3, 5, 14, 0))
    im.putalpha(Image.fromarray(a))
    return im


def draw_cta(layer, t):
    c = OV["cta"]
    k = ease_out((t - c["name_in"] + 0.3) / 0.6)
    if k <= 0:
        return
    shade = bottom_shade()
    if k < 1:
        shade = shade.copy()
        shade.putalpha(shade.getchannel("A").point(lambda v: int(v * k)))
    layer.alpha_composite(shade)
    d = ImageDraw.Draw(layer)
    # company name, typography only
    p, e, eb = entrance(t, c["name_in"], 0.5)
    if p > 0:
        f = font("Inter-ExtraBold", 58)
        txt = Image.new("RGBA", (W, 120), (0, 0, 0, 0))
        tl = tracked_len(c["name"], f, 3)
        text_tracked(ImageDraw.Draw(txt), ((W - tl) / 2, 84), c["name"], f, (255, 255, 255), 3)
        place(layer, txt, W / 2, 1404 + lerp(40, 0, e), alpha=e, blur=lerp(10, 0, e))
        # orange rule under the name
        ru = ease_out((t - c["name_in"] - 0.2) / 0.4)
        if ru > 0:
            d.rounded_rectangle([W / 2 - 60 * ru, 1446, W / 2 + 60 * ru, 1452], 3, fill=(*ORANGE, 255))
    p, e, eb = entrance(t, c["label_in"], 0.35)
    if p > 0:
        f = font("Inter-SemiBold", 38)
        txt = Image.new("RGBA", (W, 80), (0, 0, 0, 0))
        ImageDraw.Draw(txt).text((W / 2, 54), c["label"], font=f, fill=(255, 255, 255, 235), anchor="ms")
        place(layer, txt, W / 2, 1536 + lerp(16, 0, e), alpha=e)
    p, e, eb = entrance(t, c["button_in"], 0.45)
    if p > 0:
        pulse = 1 + 0.018 * math.sin(2 * math.pi * 1.1 * max(0, t - c["button_in"] - 0.6)) * clamp(t - c["button_in"] - 0.6)
        place(layer, cta_button(), W / 2, 1650 + lerp(60, 0, e), scale=lerp(0.6, 1, eb) * pulse, alpha=e)


# ---------------------------------------------------------------------------
# frame assembly
# ---------------------------------------------------------------------------

def shot_at(t):
    return next((s for s in SHOTS if s["start"] <= t < s["end"]), SHOTS[-1])


def compose_frame(i):
    t = i / FPS
    plate = base_image(t)
    sid = shot_at(t)["id"]
    ip = OV["inspection_panel"]
    if ip["in"] - 0.1 <= t <= ip["out"] + 0.25:
        k = clamp((t - ip["in"] + 0.1) / 0.3) * (1 - clamp((t - ip["out"]) / 0.25))
        plate = gblur(plate, 3 * k) * (1 - 0.3 * k)
    img = Image.fromarray(np.clip(plate, 0, 255).astype(np.uint8)).resize((W, H), Image.LANCZOS)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    if sid in OV["rain_shots"]:
        draw_rain(layer, t)
    img = img.convert("RGBA")
    img.alpha_composite(layer)
    arr = np.asarray(img.convert("RGB"), dtype=np.float32)
    if t >= OV["sparkles"]["in"]:
        arr = add_sparkles(arr, t, OV["sparkles"]["in"])
    arr = grade(arr, i)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_name_card(ui, t)
    draw_benefit_cards(ui, t)
    draw_panel(ui, t)
    draw_cta(ui, t)
    for c in CAPTIONS:
        if c.active(t):
            c.draw(ui, t)
    img.alpha_composite(ui)
    return img.convert("RGB")


def main():
    global PLACEHOLDER
    ap = argparse.ArgumentParser()
    ap.add_argument("--stills", default=None, help="comma separated times (s) -> PNGs")
    ap.add_argument("--stills-dir", default=os.path.join(ROOT, "output", "stills"))
    ap.add_argument("--placeholder", action="store_true")
    ap.add_argument("--out", default=os.path.join(ROOT, "output", "sureshield_roofing_tiktok.mp4"))
    ap.add_argument("--start", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    a = ap.parse_args()
    PLACEHOLDER = a.placeholder
    if a.stills:
        os.makedirs(a.stills_dir, exist_ok=True)
        for ts in a.stills.split(","):
            t = float(ts)
            compose_frame(round(t * FPS)).save(os.path.join(a.stills_dir, f"t{t:06.2f}.png"))
            print("still", t, flush=True)
        return
    total = TL["total_duration"]
    end = a.end if a.end is not None else total
    n0, n1 = round(a.start * FPS), round(end * FPS)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    audio = os.path.join(ROOT, TL["audio"])
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", f"{a.start:.3f}", "-i", audio,
           "-map", "0:v", "-map", "1:a", "-af", "apad", "-t", f"{(n1 - n0) / FPS:.3f}",
           "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-r", str(FPS), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", a.out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n0, n1):
        proc.stdin.write(compose_frame(i).tobytes())
        if i % 30 == 0:
            print(f"frame {i}/{n1}", flush=True)
    proc.stdin.close()
    proc.wait()
    print("wrote", a.out)


if __name__ == "__main__":
    sys.exit(main())
