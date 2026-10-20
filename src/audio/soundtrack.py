"""Original soundtrack + sound design + mix for a project.

    python src/audio/soundtrack.py --project projects/eastern_counties

Everything here is synthesised from scratch (no samples, no third-party
music), so the music is original and owned outright, which means it is
cleared for paid placements on TikTok, Instagram and Facebook alike.

Style: modern, upbeat social-ad groove at 108 BPM. Warm chord stabs, a
round sub bass, a tight kick, clap, crisp hats and shaker, and a light
pluck hook. No orchestral/trailer elements, no big drops.

Outputs (projects/<p>/assets/soundtrack/): music.wav, sfx.wav, mix.wav

To use a separately licensed track instead of the original music:
    python src/audio/soundtrack.py --project projects/<p> --music path/to/licensed_track.mp3
"""
import json
import os
import sys

import numpy as np
from scipy.signal import butter, fftconvolve, sosfilt

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJ = sys.argv[sys.argv.index("--project") + 1]
CONF = os.path.join(ROOT, PROJ, "config")
TL = json.load(open(os.path.join(CONF, "timeline.json")))
OV = json.load(open(os.path.join(CONF, "overlays.json")))
SR = 48000
DUR = TL["total_duration"]
N = int(DUR * SR)
BPM, OFFSET = 108.0, 0.305  # chosen so most scene cuts land on (or near) a beat
BEAT = 60 / BPM
rng = np.random.default_rng(7)


def beat_t(b):
    return OFFSET + b * BEAT


def track():
    return np.zeros((N, 2), np.float32)


def place(buf, sig, t, gain=1.0, pan=0.0):
    i = int(round(t * SR))
    if i >= N:
        return
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.414, sig * r * 1.414], 1)
    j0 = max(0, -i)
    i = max(0, i)
    n = min(len(sig) - j0, N - i)
    if n > 0:
        buf[i:i + n] += sig[j0:j0 + n] * gain


def lp(x, f, order=2):
    return sosfilt(butter(order, f, "low", fs=SR, output="sos"), x, axis=0)


def hp(x, f, order=2):
    return sosfilt(butter(order, f, "high", fs=SR, output="sos"), x, axis=0)


def bp(x, lo, hi, order=2):
    return sosfilt(butter(order, [lo, hi], "band", fs=SR, output="sos"), x, axis=0)


def env(n, a, d, curve=4.0):
    t = np.arange(n) / SR
    e = np.minimum(t / max(a, 1e-4), 1.0) * np.exp(-curve * np.maximum(t - a, 0) / max(d, 1e-4))
    return e.astype(np.float32)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


# ---------------------------------------------------------------------------
# instruments
# ---------------------------------------------------------------------------

def kick(len_s=0.45):
    n = int(len_s * SR)
    t = np.arange(n) / SR
    f = 46 + 110 * np.exp(-t * 32)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 7.5)
    click = hp(rng.standard_normal(n) * np.exp(-t * 350), 2500) * 0.25
    return np.tanh((s + click) * 1.6).astype(np.float32)


def clap():
    n = int(0.3 * SR)
    t = np.arange(n) / SR
    e = np.zeros(n)
    for k, dt in enumerate((0, 0.011, 0.022)):
        e += np.exp(-np.maximum(t - dt, 0) * (60 if k < 2 else 18)) * (t >= dt)
    s = bp(rng.standard_normal(n), 900, 3800) * e
    return (s * 0.8).astype(np.float32)


def hat(open_=False):
    n = int((0.22 if open_ else 0.05) * SR)
    t = np.arange(n) / SR
    s = hp(rng.standard_normal(n), 7500, 4) * np.exp(-t * (14 if open_ else 90))
    return s.astype(np.float32)


def shaker():
    n = int(0.07 * SR)
    t = np.arange(n) / SR
    s = bp(rng.standard_normal(n), 5000, 11000) * np.sin(np.pi * t / t[-1]) ** 2
    return s.astype(np.float32)


def saw(f, n, detune=0.0):
    t = np.arange(n) / SR
    ph = (f * (1 + detune) * t) % 1.0
    return (2 * ph - 1).astype(np.float32)


def chord_stab(notes, len_s, bright=1600):
    n = int(len_s * SR)
    s = np.zeros(n, np.float32)
    for m in notes:
        f = midi(m)
        for dt in (-0.006, 0.0, 0.007):
            s += saw(f, n, dt)
    s = lp(s / (len(notes) * 3), bright, 2)
    return (s * env(n, 0.006, len_s * 0.55, 3.0)).astype(np.float32)


def pad(notes, len_s, bright=900):
    n = int(len_s * SR)
    s = np.zeros(n, np.float32)
    for m in notes:
        for dt in (-0.004, 0.003):
            s += saw(midi(m), n, dt)
    s = lp(s / (len(notes) * 2), bright, 2)
    t = np.arange(n) / SR
    e = np.minimum(t / 0.35, 1) * np.minimum((len_s - t) / 0.35, 1)
    return (s * np.clip(e, 0, 1)).astype(np.float32)


def bass_note(m, len_s):
    n = int(len_s * SR)
    t = np.arange(n) / SR
    f = midi(m)
    s = np.sin(2 * np.pi * f * t) + 0.35 * lp(saw(f, n), 400)
    e = np.minimum(t / 0.008, 1) * np.exp(-t * 1.6) * np.clip((len_s - t) / 0.03, 0, 1)
    return (np.tanh(s * 1.3) * e * 0.8).astype(np.float32)


def pluck(m, len_s=0.5):
    n = int(len_s * SR)
    t = np.arange(n) / SR
    f = midi(m)
    s = 0.6 * np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t) + 0.15 * saw(f, n)
    return (lp(s, 3500) * np.exp(-t * 7)).astype(np.float32)


def reverb(x, secs=1.6, wet=0.22):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = np.stack([rng.standard_normal(n), rng.standard_normal(n)], 1) * np.exp(-t * 5.5)[:, None]
    ir = lp(ir, 5000)
    ir /= np.sqrt((ir ** 2).sum(0, keepdims=True))
    y = np.stack([fftconvolve(x[:, c], ir[:, c])[:len(x)] for c in range(2)], 1)
    return x + y * wet


def delay(x, t_s, fb=0.35, mix=0.25):
    d = int(t_s * SR)
    y = x.copy()
    for k in range(1, 5):
        sh = np.zeros_like(x)
        sh[d * k:] = x[:-d * k] * (fb ** k)
        y += sh[:, ::-1] * mix if k % 2 else sh * mix  # ping-pong
    return y


# ---------------------------------------------------------------------------
# arrangement (beats counted from OFFSET; 4 beats per bar)
# ---------------------------------------------------------------------------
# progression (C major, bright & confident): Cmaj9 - Am9 - Fmaj9 - G6
PROG = [
    dict(root=36, chord=[60, 64, 67, 71, 74]),
    dict(root=33, chord=[57, 60, 64, 67, 71]),
    dict(root=29, chord=[57, 60, 64, 65, 69]),
    dict(root=31, chord=[59, 62, 64, 67, 71]),
]
HOOK = [76, 74, 72, 74, 76, 79, 76, 74]  # 8th-note pluck motif


def section_energy(t):
    """0 = intro, 1 = groove, 2 = full; follows the story beats."""
    if t < 8.4:
        return 0
    if t < 20.3:
        return 2 if t >= 10.8 else 1
    if t < 27.1:
        return 1
    if t < 36.5:
        return 2
    if t < 39.7:
        return 1
    return 3


def build_music():
    drums, bass, harm, top = track(), track(), track(), track()
    K, C, H, HO, SH = kick(), clap(), hat(), hat(True), shaker()
    total_beats = int((DUR - OFFSET) / BEAT) + 2
    kick_times = []
    for b in range(-1, total_beats):
        t = beat_t(b)
        if t < 0 or t > DUR - 0.3:
            continue
        e = section_energy(t)
        bar_b = b % 4
        # kick: four-on-the-floor from the groove; soft half-time in the intro
        if e >= 1 or bar_b in (0, 2):
            g = 0.55 if e == 0 else (0.8 if e == 1 else 0.95)
            place(drums, K, t, g)
            kick_times.append(t)
        if e >= 2 and bar_b in (1, 3):
            place(drums, C, t, 0.42, 0.05)
        # offbeat hats + shaker 16ths
        place(drums, HO if (e >= 2 and bar_b == 3) else H, t + BEAT / 2, 0.22 if e else 0.15, 0.25)
        for s16 in range(4):
            place(drums, SH, t + s16 * BEAT / 4, (0.06 + 0.03 * (s16 % 2)) * (1.0 if e else 0.7), -0.3)
        if e == 3:
            place(drums, H, t + BEAT * 0.75, 0.12, 0.4)
    # harmony: one chord per bar
    for bar in range(-1, total_beats // 4 + 1):
        t = beat_t(bar * 4)
        if t > DUR:
            break
        pc = PROG[bar % 4]
        e = section_energy(max(t, 0))
        if t >= -BEAT * 4:
            place(harm, pad(pc["chord"], BEAT * 4 + 0.3, 700 if e == 0 else 1100), max(t, 0), 0.18, 0)
        if e >= 1:
            for k, off in enumerate((0, 1.5, 2.5, 3.5)):  # syncopated stabs
                if e == 1 and k % 2:
                    continue
                place(harm, chord_stab(pc["chord"], 0.32, 1500 if e == 1 else 2200), t + off * BEAT, 0.28,
                      -0.15 if k % 2 else 0.15)
            for off, ln in ((0, 1.4), (1.5, 0.45), (2.0, 1.4), (3.5, 0.45)):
                place(bass, bass_note(pc["root"], ln * BEAT), t + off * BEAT, 0.6)
        if e >= 2 and t >= 27.0 or e == 3:
            for k, m in enumerate(HOOK):
                if (bar % 2) and k >= 4:
                    m = HOOK[k - 4] - 2
                place(top, pluck(m), t + k * BEAT / 2, 0.16, 0.3 if k % 2 else -0.3)
    top = delay(top, BEAT * 0.75, 0.38, 0.35)
    # sidechain pump on bass + harmony from the kick
    pump = np.ones(N, np.float32)
    for kt in kick_times:
        i = int(kt * SR)
        n = int(0.28 * SR)
        seg = 1 - 0.55 * np.exp(-np.arange(n) / SR * 14)
        j = min(N, i + n)
        pump[i:j] = np.minimum(pump[i:j], seg[:j - i])
    bass *= pump[:, None]
    harm *= pump[:, None] ** 0.7
    music = drums + lp(bass, 220) * 0.9 + reverb(harm, 1.4, 0.25) + reverb(top, 1.8, 0.3)
    # "weather turns": music dips into a filtered breakdown, then lifts
    t = np.arange(N) / SR
    wet = np.clip((t - 25.0) / 0.6, 0, 1) * np.clip((27.05 - t) / 0.25, 0, 1)
    music = music * (1 - wet[:, None]) + lp(music, 700) * wet[:, None]
    fade = np.clip(t / 0.25, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1)
    return (music * fade[:, None]).astype(np.float32)


# ---------------------------------------------------------------------------
# sound design
# ---------------------------------------------------------------------------

def whoosh(len_s=0.42, lo=300, hi=6000, gain=1.0):
    n = int(len_s * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n).astype(np.float32)
    out = np.zeros(n, np.float32)
    seg = n // 12
    for k in range(12):  # sweeping band-pass
        u = k / 11
        fc = lo * (hi / lo) ** (np.sin(np.pi * u) * 0.9 + 0.1 * u)
        a, b = k * seg, min(n, (k + 1) * seg + seg // 2)
        out[a:b] += bp(x[a:b], fc * 0.6, min(fc * 1.6, 20000)) * np.hanning(b - a)
    e = np.sin(np.pi * t / len_s) ** 1.5
    return out * e * gain


def ui_pop(f0=1200, f1=700, len_s=0.09):
    n = int(len_s * SR)
    t = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-t * 40)
    return (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 45)).astype(np.float32)


def soft_click():
    n = int(0.03 * SR)
    t = np.arange(n) / SR
    return (bp(rng.standard_normal(n), 2000, 6000) * np.exp(-t * 220)).astype(np.float32)


def block_clack(f=420):
    n = int(0.12 * SR)
    t = np.arange(n) / SR
    body = np.sin(2 * np.pi * f * t) * np.exp(-t * 55) + 0.6 * np.sin(2 * np.pi * f * 2.7 * t) * np.exp(-t * 80)
    noise = bp(rng.standard_normal(n), 1500, 5000) * np.exp(-t * 160) * 0.5
    return (body + noise).astype(np.float32) * 0.6


def chime(notes=(84, 91), len_s=1.2):
    n = int(len_s * SR)
    t = np.arange(n) / SR
    s = np.zeros(n, np.float32)
    for k, m in enumerate(notes):
        tt = np.maximum(t - k * 0.09, 0)
        f = midi(m)
        s += ((np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * f * 2.01 * tt)) * np.exp(-tt * 4) * (t >= k * 0.09))
    return s * 0.5


def impact():
    n = int(1.2 * SR)
    t = np.arange(n) / SR
    sub = np.sin(2 * np.pi * (38 + 40 * np.exp(-t * 18)) * t) * np.exp(-t * 3.2)
    air = lp(rng.standard_normal(n), 3000) * np.exp(-t * 6) * 0.25
    return np.tanh((sub + air) * 1.2).astype(np.float32)


def riser(len_s=1.1):
    n = int(len_s * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    out = np.zeros(n)
    seg = n // 10
    for k in range(10):
        a, b = k * seg, min(n, (k + 1) * seg + seg // 2)
        fc = 400 * (8000 / 400) ** (k / 9)
        out[a:b] += bp(x[a:b], fc * 0.7, min(fc * 1.4, 20000)) * np.hanning(b - a)
    return (out * (t / len_s) ** 2).astype(np.float32)


def shimmer(len_s=2.0):
    n = int(len_s * SR)
    s = np.zeros(n, np.float32)
    for k in range(14):
        i = int(rng.uniform(0, 0.75) * n)
        m = rng.choice([84, 88, 91, 96, 100])
        tone = pluck(m, 0.6) * 0.5
        j = min(n, i + len(tone))
        s[i:j] += tone[:j - i]
    return s


def wind(len_s):
    n = int(len_s * SR)
    t = np.arange(n) / SR
    x = rng.standard_normal(n)
    gust = 0.5 + 0.5 * np.sin(2 * np.pi * 0.35 * t) * np.sin(2 * np.pi * 0.13 * t + 1)
    s = lp(bp(x, 200, 1400), 900) * gust * np.minimum(t / 0.6, 1) * np.minimum((len_s - t) / 0.5, 1)
    return s.astype(np.float32)


def build_sfx():
    fx = track()
    place(fx, impact(), 0.02, 0.55)  # opening accent on the hook
    # transitions
    shots = TL["shots"]
    for i in range(1, len(shots)):
        a, b = shots[i - 1]["id"], shots[i]["id"]
        kind = OV["transitions"].get(f"{a}>{b}", OV["transitions"]["default"])
        tc = shots[i]["start"]
        if kind == "whip":
            w = whoosh(0.42, 350, 7000)
            place(fx, w, tc - 0.21, 0.32, pan=0.0)
        else:
            w = whoosh(0.7, 500, 3000)
            place(fx, lp(w, 2500), tc - 0.35, 0.22)
    # UI entrances (cards, panels, label, name card) - soft pops, not every word
    ui = []
    for nc in OV.get("name_cards", []):
        ui.append((nc["in"], 900))
    for lb in OV.get("labels", []):
        ui.append((lb["in"], 1100))
    for st in OV.get("card_stacks", []):
        for k, c in enumerate(st["cards"]):
            ui.append((c["in"], 1000 + 120 * k))
    for p in OV.get("panels", []):
        ui.append((p["in"], 850))
        if "badge" in p:
            ui.append((p["badge"]["in"], 1300))
        if p.get("type") == "booking":
            for k in range(10):
                tt = p["fill_from"] + (p["fill_to"] - p["fill_from"]) * k / 10
                place(fx, soft_click(), tt + 0.03, 0.18, pan=((k % 4) - 1.5) / 3)
        for c in p.get("circles", []):
            place(fx, whoosh(0.3, 1500, 5000), c[3], 0.08)
    for t_in, f in ui:
        place(fx, ui_pop(f * 1.4, f * 0.8), t_in + 0.02, 0.22)
    # practical sounds: blocks set in e5, mallet in e7c, rows landing in e7a/e7b
    for k in range(6):
        place(fx, block_clack(380 + 30 * (k % 3)), 15.5 + k * 0.75, 0.2, pan=0.2)
    for k in range(3):
        place(fx, block_clack(300), 31.45 + 0.2 + k * 0.17 * 2, 0.22)
    for k in range(9):
        place(fx, block_clack(420 + 25 * (k % 4)), 27.6 + 0.12 + k * 0.2, 0.08, pan=(k % 3 - 1) * 0.3)
    for k in range(6):
        place(fx, block_clack(360), 30.32 + k * 0.13, 0.08)
    # weather turns: gust + rain bed
    place(fx, wind(2.3), 24.9, 0.28)
    rain = hp(rng.standard_normal(int(1.8 * SR)), 3000) * 0.05
    rain *= np.minimum(np.arange(len(rain)) / SR / 0.6, 1) * np.minimum((len(rain) / SR - np.arange(len(rain)) / SR) / 0.4, 1)
    place(fx, rain.astype(np.float32), 25.5, 1.0)
    # lift back into the transformation
    place(fx, riser(1.0), 26.1, 0.16)
    place(fx, impact(), 27.1, 0.18)
    # CTA: sparkle shimmer, success chime on the button, soft click on contact
    place(fx, shimmer(2.2), 39.7, 0.2)
    cta = OV["cta"]
    place(fx, chime(), cta["button_in"] + 0.05, 0.22)
    if cta.get("contact_in"):
        place(fx, ui_pop(1500, 900), cta["contact_in"] + 0.03, 0.18)
    return reverb(fx, 1.0, 0.15).astype(np.float32)


# ---------------------------------------------------------------------------
# mix
# ---------------------------------------------------------------------------

def load_vo():
    import subprocess
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", os.path.join(ROOT, TL["audio"]), "-f", "f32le", "-ac", "2",
                          "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).reshape(-1, 2)
    out = np.zeros((N, 2), np.float32)
    out[:min(N, len(vo))] = vo[:N]
    return out


def follower(x, attack=0.02, release=0.35, hop=48):
    """Envelope follower (1 ms control rate) used to duck the music under speech."""
    mono = np.abs(x).mean(1)
    k = int(0.02 * SR)
    rms = np.sqrt(np.convolve(mono ** 2, np.ones(k) / k, "same"))[::hop]
    ca, cr = np.exp(-hop / (attack * SR)), np.exp(-hop / (release * SR))
    out = np.empty_like(rms)
    v = 0.0
    for i, target in enumerate(rms):
        c = ca if target > v else cr
        v = c * v + (1 - c) * target
        out[i] = v
    return np.repeat(out, hop)[:len(x)]


def write_wav(path, x):
    import wave
    y = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((y * 32767).astype("<i2").tobytes())


def db(x):
    return 10 ** (x / 20)


def main():
    out_dir = os.path.join(ROOT, PROJ, "assets", "soundtrack")
    os.makedirs(out_dir, exist_ok=True)
    if "--music" in sys.argv:  # swap in a separately licensed track (looped/trimmed to length)
        import subprocess
        src = sys.argv[sys.argv.index("--music") + 1]
        raw = subprocess.run(["ffmpeg", "-v", "error", "-stream_loop", "-1", "-i", src, "-t", str(DUR), "-f", "f32le",
                              "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
        music = np.zeros((N, 2), np.float32)
        ext = np.frombuffer(raw, np.float32).reshape(-1, 2)[:N]
        music[:len(ext)] = ext
        t = np.arange(N) / SR
        music *= (np.clip(t / 0.3, 0, 1) * np.clip((DUR - t) / 1.2, 0, 1))[:, None]
    else:
        music = build_music()
    sfx = build_sfx()
    vo = load_vo()
    vo = vo / (np.abs(vo).max() + 1e-9) * db(-3)
    music = music / (np.abs(music).max() + 1e-9)
    sfx = sfx / (np.abs(sfx).max() + 1e-9)
    # auto-ducking: music sits ~15 dB under the voice while it speaks, lifts in the gaps
    env_vo = follower(vo)
    speech = np.clip(env_vo / (np.percentile(env_vo[env_vo > 1e-4], 60) + 1e-9), 0, 1)
    duck = db(-13) * (1 - speech) + db(-22) * speech
    mix = vo + music * duck[:, None] + sfx * db(-14)
    write_wav(os.path.join(out_dir, "music.wav"), music * db(-6))
    write_wav(os.path.join(out_dir, "sfx.wav"), sfx * db(-6))
    peak = np.abs(mix).max()
    mix = mix / peak * db(-1.5)
    raw = os.path.join(out_dir, "mix_raw.wav")
    write_wav(raw, mix)
    # two-pass EBU R128 loudness normalisation to the social-video target
    import subprocess
    meas = subprocess.run(["ffmpeg", "-nostats", "-i", raw, "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                           "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(meas[meas.rindex("{"):meas.rindex("}") + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:"
          f"measured_LRA={j['input_lra']}:measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", af, "-ar", str(SR),
                    os.path.join(out_dir, "mix.wav")], check=True)
    print("ok", out_dir, f"pre-norm peak {20 * np.log10(peak):.1f} dBFS")


if __name__ == "__main__":
    main()
