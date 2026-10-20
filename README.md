# Fenland Drives & Patios Ltd: animated TikTok/Reels ad

This is a 9:16 3D cartoon ad (1080×1920, 30 fps, H.264/AAC, 37 s). It is
synchronised to the supplied British male ElevenLabs voiceover and styled
after the reference video `Oct-20Footage1`.

**Final video:** `output/fenland_drives_patios_tiktok.mp4`
**Contact sheet:** `output/contact_sheet.png`
**Style analysis:** `docs/reference_style_analysis.md`

## Layout
```
assets/audio/voiceover.mp3     original narration (unchanged)
assets/logo/fenland_logo.png   supplied logo (only ever scaled uniformly)
config/asr_words.json          word timestamps detected from the real MP3
config/timeline.json           shots, caption chunks + word times, card events
src/make_timeline.py           builds timeline.json (verbatim transcript aligned to ASR times)
src/blender/lib.py             render setup, materials, primitives, keyframe helpers
src/blender/character.py       cartoon character rig (expressions, blinks, 2-bone IK arms)
src/blender/sets.py            house/street, herringbone block paving, garden, props, mascot, lights
src/blender/shots.py           the 12 shots (set, cast, acting, camera)
src/blender/render_shot.py     renders one shot to build/frames/<shot>/NNNN.png
src/composite.py               captions, cards, logo, particles, transitions, grade -> MP4
src/make_audio.py              music bed + SFX under the voiceover -> build/mix.wav
src/contact_sheet.py           1-fps contact sheet of the final video
build/render_all.sh            renders every shot (resumable)
```

## Re-rendering
Requirements: Python 3.13, ffmpeg, Pillow and numpy, plus Blender as a
Python module (`pip install bpy`) in a virtualenv. Inter fonts must be in
`/usr/share/fonts/opentype/inter/`.

```bash
python3 -m venv ~/venv && ~/venv/bin/pip install bpy numpy pillow
python3 src/make_timeline.py            # only if captions/shots/cards change
./build/render_all.sh                   # 3D plates (~9 s/frame on 4 CPU cores, ~2.7 h)
python3 src/make_audio.py               # build/mix.wav
python3 src/composite.py                # build/video_noaudio.mp4
ffmpeg -i build/video_noaudio.mp4 -i build/mix.wav -map 0:v -map 1:a -c:v copy \
       -c:a aac -b:a 192k -shortest output/fenland_drives_patios_tiktok.mp4
python3 src/contact_sheet.py
```

To re-render a single shot:
`~/venv/bin/python src/blender/render_shot.py s4_team`

To preview frames quickly, add `--frames 1,60 --samples 4 --res 270x480 --out build/preview`.

To get composited stills: `python3 src/composite.py --frames 300,900`
(the stills are written to `build/stills/`).

The word timings came from the actual MP3, using faster-whisper
(`small.en`). The on-screen text is always the supplied transcript, so
ASR mishearings such as "reserves" for "deserves" are never shown.

## Content rules followed
- All business details come from the client brief: the name, Lawrence, the
  phone number, the website and PE12 7LD with a 30-mile radius. The £50/day
  budget is not shown.
- The ad contains no invented prices, testimonials, awards, accreditations
  or guarantees. The "risk" cards describe generic poor workmanship and do
  not name or depict any real company.
