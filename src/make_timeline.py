"""Build config/timeline.json: shots, verbatim caption chunks with per-word
times (supplied transcript text aligned onto faster-whisper word timestamps
from the real MP3), and on-screen card events.

Run: python3 src/make_timeline.py
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FPS = 30
DURATION = 37.0  # 36.2 s narration + short CTA hold

# Verbatim transcript, chunked for on-screen captions. *word* = orange highlight.
CHUNKS = [
    "When you're investing in your *home's* *exterior,*",
    "letting an *unreliable* *contractor*",
    "touch your *property*",
    "is a *massive* *risk* that no homeowner wants to take.",
    "Across the *region* and all surrounding areas,",
    "*Lawrence* and the team at",
    "*Fenland* *Drives* *and* *Patios* *Ltd*",
    "have built a *rock-solid* *reputation*",
    "on absolute *trust,* *transparent* *pricing*",
    "and *elite* *craftsmanship* with *zero* *cut* *corners*",
    "or *hidden* *fees.*",
    "Whether you need a stunning new *driveway,*",
    "a durable *patio* installation",
    "or expert *hard* *landscaping,*",
    "our *experienced* *local* *team* handles your property",
    "with the *precision* and *care* it deserves,",
    "so you can *transform* your *outdoor* *space*",
    "with complete *peace* *of* *mind.*",
    "*Stop* *gambling* on uncertain contractors",
    "and secure your *free,* no-obligation *quote* *today.*",
]

SHOTS = [  # name, start, end (seconds)
    ("s1_exterior", 0.00, 3.85),
    ("s2_worry", 3.85, 6.75),
    ("s3_region", 6.75, 9.15),
    ("s4_team", 9.15, 13.25),
    ("s5a_laying", 13.25, 15.95),
    ("s5b_level", 15.95, 18.90),
    ("s6a_drive", 18.90, 20.95),
    ("s6b_patio", 20.95, 22.40),
    ("s6c_hardland", 22.40, 24.20),
    ("s7_finish", 24.20, 28.35),
    ("s8_reveal", 28.35, 31.65),
    ("s9_cta", 31.65, DURATION),
]

# transitions at every cut: style of the reference (directional blur whip)
TRANSITIONS = {
    "s1_exterior": "blur", "s2_worry": "whip_left", "s3_region": "zoom",
    "s4_team": "whip_left", "s5a_laying": "whip_up", "s5b_level": "whip_left",
    "s6a_drive": "whip_left", "s6b_patio": "whip_left", "s6c_hardland": "whip_left",
    "s7_finish": "whip_left", "s8_reveal": "blur",
}

CARDS = [
    # kind, start, end, payload
    {"kind": "tag", "start": 4.15, "end": 6.75, "text": "DON'T RISK YOUR PROPERTY",
     "color": "red"},
    {"kind": "stack", "start": 4.45, "end": 6.75, "items": [
        {"t": 4.45, "num": "1", "title": "Sinking blocks", "sub": "uneven, poorly prepared base",
         "accent": "orange"},
        {"t": 4.95, "num": "2", "title": "Weeds & cracks", "sub": "gaps left in the joints",
         "accent": "orange"},
        {"t": 5.45, "num": "3", "title": "Surprise extras", "sub": "costs added at the end",
         "accent": "red"}]},
    {"kind": "map", "start": 7.25, "end": 9.15, "title": "PE12 7LD",
     "sub": "& surrounding areas · 30-mile radius"},
    {"kind": "logo", "start": 10.0, "end": 13.25},
    {"kind": "tag", "start": 12.25, "end": 13.25, "text": "BUILT ON TRUST", "color": "orange"},
    {"kind": "stack", "start": 14.75, "end": 18.9, "check": True, "items": [
        {"t": 14.75, "num": "", "title": "Transparent pricing", "sub": "clear quotes, explained up front",
         "accent": "green"},
        {"t": 15.85, "num": "", "title": "Quality craftsmanship", "sub": "zero cut corners",
         "accent": "green"},
        {"t": 18.0, "num": "", "title": "No hidden fees", "sub": "what you agree is what you pay",
         "accent": "green"}]},
    {"kind": "chips", "start": 20.0, "end": 24.2, "items": [
        {"t": 20.0, "text": "STUNNING NEW DRIVEWAYS"},
        {"t": 21.4, "text": "DURABLE PATIOS"},
        {"t": 23.2, "text": "EXPERT HARD LANDSCAPING"}]},
    {"kind": "report", "start": 25.0, "end": 28.35, "header": "PROJECT CHECK",
     "badge": "DETAIL", "foot": "Precision & care on every joint", "image": "s5a_laying"},
    {"kind": "tag", "start": 28.65, "end": 31.65, "text": "TRANSFORM YOUR OUTDOOR SPACE",
     "color": "orange"},
    {"kind": "stack", "start": 30.1, "end": 31.65, "check": True, "items": [
        {"t": 30.1, "num": "", "title": "Complete peace of mind", "sub": "local, experienced team",
         "accent": "green"}]},
    {"kind": "cta", "start": 32.0, "end": DURATION, "logo_t": 32.0, "button_t": 33.9,
     "button": "GET YOUR FREE QUOTE", "sub_t": 34.6, "sub": "FREE, NO-OBLIGATION QUOTE",
     "phone": "07455 358300", "web": "fenlanddrivesandpatios.co.uk", "contact_t": 35.0},
]


def norm(w):
    return re.sub(r"[^a-z0-9]", "", w.lower())


def main():
    asr = json.load(open(os.path.join(ROOT, "config", "asr_words.json")))
    # merge hyphen continuation tokens ("rock" "-solid")
    merged = []
    for a in asr:
        if a["w"].startswith("-") and merged:
            merged[-1] = {"w": merged[-1]["w"] + a["w"], "s": merged[-1]["s"], "e": a["e"]}
        else:
            merged.append(dict(a))
    # ASR heard "contractor touch" as "contract to touch"
    for i in range(len(merged) - 1):
        if norm(merged[i]["w"]) == "contract" and norm(merged[i + 1]["w"]) == "to":
            merged[i] = {"w": "contractor", "s": merged[i]["s"], "e": merged[i + 1]["e"]}
            del merged[i + 1]
            break
    words = []
    for ci, ch in enumerate(CHUNKS):
        for tok in ch.split():
            hl = tok.startswith("*")
            words.append({"text": tok.strip("*"), "hl": hl, "chunk": ci})
    assert len(words) == len(merged), (len(words), len(merged))
    mismatches = []
    for w, a in zip(words, merged):
        w["s"], w["e"] = a["s"], a["e"]
        if norm(w["text"]) != norm(a["w"]):
            mismatches.append((w["text"], a["w"]))
    chunks = []
    for ci in range(len(CHUNKS)):
        ws = [w for w in words if w["chunk"] == ci]
        chunks.append({"start": ws[0]["s"], "words": [
            {"text": w["text"], "hl": w["hl"], "s": w["s"], "e": w["e"]} for w in ws]})
    for i, c in enumerate(chunks):
        c["end"] = chunks[i + 1]["start"] if i + 1 < len(chunks) else DURATION
    shots = []
    for name, s, e in SHOTS:
        f0, f1 = round(s * FPS), round(e * FPS)
        shots.append({"name": name, "start": s, "end": e, "frame_start": f0,
                      "frames": f1 - f0, "transition_out": TRANSITIONS.get(name)})
    out = {"fps": FPS, "width": 1080, "height": 1920, "duration": DURATION,
           "total_frames": round(DURATION * FPS), "audio": "assets/audio/voiceover.mp3",
           "shots": shots, "captions": chunks, "cards": CARDS,
           "asr_text_corrections": mismatches}
    json.dump(out, open(os.path.join(ROOT, "config", "timeline.json"), "w"), indent=1)
    print("frames", sum(s["frames"] for s in shots), "corrections", mismatches)


if __name__ == "__main__":
    main()
