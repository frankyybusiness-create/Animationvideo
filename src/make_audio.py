"""Synthesise the subtle music bed + sound effects and mix under the original
voiceover. The narration itself is never edited: it is placed at t=0 with a
single constant gain (to reach ~-14 LUFS for social), no time-stretch or cuts.

Output: build/mix.wav (48 kHz stereo)
"""
import json
import os
import subprocess
import wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TL = json.load(open(os.path.join(ROOT, "config", "timeline.json")))
SR = 48000
DUR = TL["duration"]
N = int(DUR * SR)
rng = np.random.RandomState(4)


def db(x):
    return 10 ** (x / 20)


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):  # simple one-pole (short signals only)
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def fft_filter(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def env_adsr(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    e[:na] = np.linspace(0, 1, na)
    e[-nr:] *= np.linspace(1, 0, nr)
    return e


def music_bed():
    """Warm, slow pad: I - vi - IV - V in D major, filtered saw + sine."""
    out = np.zeros((N, 2))
    chords = [(62, 66, 69, 74), (59, 62, 66, 71), (55, 59, 62, 67), (57, 61, 64, 69)]
    bar = 4.0
    t = 0.0
    k = 0
    while t < DUR:
        n = int(min(bar + 1.0, DUR - t + 0.5) * SR)
        tt = np.arange(n) / SR
        sig = np.zeros(n)
        for m in chords[k % 4]:
            fr = 440 * 2 ** ((m - 69) / 12)
            for det in (-0.12, 0.12):
                ph = 2 * np.pi * fr * (1 + det / 100) * tt
                sig += 0.5 * np.sin(ph) + 0.12 * np.sin(2 * ph) + 0.05 * np.sin(3 * ph)
        bass = 440 * 2 ** ((chords[k % 4][0] - 12 - 69) / 12)
        sig += 0.9 * np.sin(2 * np.pi * bass * tt)
        sig *= env_adsr(n, 1.2, 1.4)
        s0 = int(t * SR)
        s1 = min(N, s0 + n)
        L = s1 - s0
        out[s0:s1, 0] += sig[:L]
        out[s0:s1, 1] += np.roll(sig, 240)[:L]
        t += bar
        k += 1
    # soft plucked arpeggio from the "solution" section onwards (warmer mood)
    arp = [74, 78, 81, 78]
    t = 9.2
    i = 0
    while t < DUR - 0.5:
        m = arp[i % 4] + (0 if (int(t / 4) % 2 == 0) else -3)
        fr = 440 * 2 ** ((m - 69) / 12)
        n = int(0.9 * SR)
        tt = np.arange(n) / SR
        p = np.sin(2 * np.pi * fr * tt) * np.exp(-tt * 5) * 0.35
        s0 = int(t * SR)
        s1 = min(N, s0 + n)
        out[s0:s1, 0] += p[: s1 - s0] * 0.8
        out[s0:s1, 1] += p[: s1 - s0] * 1.0
        t += 0.5
        i += 1
    peak = np.abs(out).max()
    out = out / peak
    # darker during the "problem" section, opening up at the team reveal
    gain = np.interp(np.arange(N) / SR, [0, 8.5, 9.6, DUR - 1.2, DUR], [0.55, 0.6, 1.0, 1.0, 0.0])
    fade_in = np.clip(np.arange(N) / (0.6 * SR), 0, 1)
    return out * (gain * fade_in)[:, None]


def whoosh(length=0.45):
    n = int(length * SR)
    x = rng.normal(0, 1, n)
    x = fft_filter(x, 300, 5000)
    e = np.sin(np.linspace(0, np.pi, n)) ** 2
    return x * e / (np.abs(x).max() + 1e-9)


def pop():
    n = int(0.12 * SR)
    tt = np.arange(n) / SR
    fr = 900 * np.exp(-tt * 18) + 380
    ph = 2 * np.pi * np.cumsum(fr) / SR
    return np.sin(ph) * np.exp(-tt * 38)


def sparkle():
    n = int(1.2 * SR)
    tt = np.arange(n) / SR
    s = np.zeros(n)
    for i, m in enumerate((88, 91, 95, 100, 103)):
        fr = 440 * 2 ** ((m - 69) / 12)
        d = int(i * 0.07 * SR)
        s[d:] += np.sin(2 * np.pi * fr * tt[: n - d]) * np.exp(-tt[: n - d] * 6)
    return s / np.abs(s).max()


def place(buf, clip, t, gain, pan=0.0):
    s0 = int(t * SR)
    s1 = min(N, s0 + len(clip))
    if s0 >= N:
        return
    c = clip[: s1 - s0] * gain
    buf[s0:s1, 0] += c * (1 - max(0, pan))
    buf[s0:s1, 1] += c * (1 + min(0, pan))


def write_wav(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main():
    build = os.path.join(ROOT, "build")
    vo_wav = os.path.join(build, "vo48.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i",
                    os.path.join(ROOT, TL["audio"]), "-ar", str(SR), "-ac", "2", vo_wav],
                   check=True)
    with wave.open(vo_wav) as w:
        vo = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2) / 32768.0
    voice = np.zeros((N, 2))
    voice[: min(N, len(vo))] = vo[:N]
    VO_GAIN = db(4.5)  # -19.3 LUFS -> ~-14.8 LUFS, constant gain only

    sfx = np.zeros((N, 2))
    for s in TL["shots"][1:]:
        place(sfx, whoosh(), s["start"] - 0.22, 0.22, 0.0)
    for c in TL["cards"]:
        times = [it["t"] for it in c.get("items", [])] or [c["start"]]
        if c["kind"] == "cta":
            times = [c["logo_t"], c["button_t"]]
        for tm in times:
            place(sfx, pop(), tm, 0.16)
    place(sfx, sparkle(), TL["shots"][-1]["start"] + 0.1, 0.12)
    place(sfx, sparkle(), 33.5, 0.08)  # mascot wink
    # light rain ambience under the opening night shots
    n = int(6.9 * SR)
    rain = fft_filter(rng.normal(0, 1, n), 1500, 9000)
    rain = rain / np.abs(rain).max() * np.interp(np.arange(n), [0, SR * 0.3, n - SR * 0.6, n],
                                                 [0, 1, 1, 0])
    RAIN = 0.0  # daytime version: no rain ambience
    sfx[:n, 0] += rain * RAIN
    sfx[:n, 1] += np.roll(rain, 400) * RAIN

    music = music_bed() * db(-27)
    mix = voice * VO_GAIN + music + sfx
    peak = np.abs(mix).max()
    if peak > 0.98:
        mix *= 0.98 / peak
    write_wav(os.path.join(build, "mix.wav"), mix)
    print("peak", peak)


if __name__ == "__main__":
    main()
