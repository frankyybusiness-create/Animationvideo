# Sureshield Roofing Limited — 9:16 cartoon advert

Final video: `output/sureshield_roofing_tiktok.mp4` (1080×1920, 30 fps, H.264 + AAC, ~37.2 s)
Contact sheet: `output/contact_sheet.jpg`

The only style reference is **Oct-20Footage1**
(`https://github.com/frankyybusiness-create/Animationvideo/releases/download/Fottage1/Oct-20Footage1`).
The voiceover (`assets/voiceover.mp3`) is the original British male recording, unedited. It is the master timeline.

## What I took from Oct-20Footage1

I downloaded the file (QuickTime, 1080×1920, 30 fps, 19.0 s), extracted frames at 2 fps plus 10 fps around every cut, and sampled pixel colours.

| Area | What the reference does | How this advert matches it |
|---|---|---|
| Rendering | Dimensional toy or clay 3D. Rounded-cube head about 40 % of body height, big glossy eyes, simple capsule limbs, knit and fabric textures with real bump, soft subsurface skin | The scenes are real 3D, rendered in Blender Cycles from rounded primitives. Skin uses subsurface scattering, the knit and tweed materials use bump, and the eyes have a glossy clear coat |
| World and light | Rainy British night: deep navy (`#030815`), warm practical lights, orange key against a cool blue rim, strong shallow depth of field with warm bokeh | The same navy world gradient, warm key light, blue rim light and moonlight, lit windows and street lamps that blur into bokeh, wide-aperture DOF, and 2D rain streaks on exterior shots |
| Captions | Top-left at x≈68. Inter Bold about 80 px, white, sentence case. Each word rises in from a dim, slightly lower state. Key words turn orange (`#F76A32`) with a drawn-on underline. The caption dims out on the cut | The same layout, font, size, word-rise animation, orange highlight with underline, and dim-out. Word times come from a word-level alignment of the real voiceover |
| Cards | Cream (`#F7F2EB`) rounded cards with a coloured left accent strip, a circular badge, a bold title and a grey sub-line. A slight tilt and soft shadow. Each card resolves out of a blur and dark tint, settles, and hovers independently | Benefit cards (Scene 4) and the company-name card (Scene 3) follow the same design and motion |
| Report panel | "ROOF REPORT" panel with a tracked header, a pill at top right, a roof photo inset with rounded corners, orange circles drawn on, and an orange badge with a check | The "ROOF INSPECTION" panel (Scene 5) uses the same structure. It shows a separate close-up render of the damaged tiles |
| CTA | Small label above a large rounded pill button with a glow, on a dark ground, with golden sparkle particles | Company name in type only, the label "Free, no-obligation quote", and a green pill button with a glow and a gentle pulse. Golden sparkles in the last scene |
| Cuts | Fast whip pans with heavy horizontal motion blur, defocus dissolves into UI-heavy shots, slow push-ins | Whip-pan cuts with horizontal motion blur. Defocus dissolves around the inspection panel and into the interior shot. Every shot has a camera push or crane |

The main character is new. **Arthur** is a British homeowner in a tweed flat cap, with a grey moustache and sideburns, no glasses, and a bottle-green knit cardigan. He uses the same toy proportions as the reference character, which has a beanie and glasses. The supporting cast is also new: two Sureshield roofers in hard hats and hi-vis, and a generic fictional "careless contractor" in a backwards red cap.

There is **no logo or shield mark** anywhere. The company name appears as text only. The advert has no phone number, website, prices, certifications, or guarantees.

## Storyboard and timing

All times are on the voiceover timeline. Word timings are in `config/voiceover_words.json`.

| Shot | Time (s) | Content | Caption |
|---|---|---|---|
| s1 | 0.00–4.16 | Crane from the damaged roof tiles down to a worried Arthur | A **compromised** roof? |
| s2a | 4.16–7.10 | Careless contractor shrugs as a tile falls and shatters. Arthur is alarmed | Don't **risk** your home. |
| s2b | 7.10–9.55 | Wide street of terraced homes | Across the **region.** |
| s3 | 9.55–14.30 | Sureshield team inspects the house. Name card | Built on **trust.** |
| s4 | 14.30–19.70 | A roofer places a tile carefully. Three benefit cards | Elite **craftsmanship.** / Zero cut **corners.** |
| s5a | 19.70–21.80 | Roof inspection panel | Leaks. |
| s5b | 21.80–23.50 | Roofer repairing a damaged section | … Repairs. |
| s5c | 23.50–25.20 | New tiles drop into place row by row | … **New roofs.** |
| s6a | 25.20–29.10 | Finished roof. Team waves, Arthur relieved | Our **local** team. / Precision. **Care.** |
| s6b | 29.10–31.60 | Arthur in his armchair with tea as lightning hits outside | … **Peace of mind.** |
| s7 | 31.60–37.20 | Finished home, Arthur waves, CTA | Stop **gambling.** / Secure your **free quote** today. |

The video runs 1 s past the end of the voice (36.2 s) so the CTA can be read. The final word is not cut off.

## Project layout

```
assets/voiceover.mp3            original VO (unchanged)
config/timeline.json            shot boundaries (scene cut points chosen in speech gaps)
config/overlays.json            caption words/timings, cards, panel, CTA, transitions
config/voiceover_words.json     word-level alignment of the VO (faster-whisper)
src/scene3d/lib.py              procedural characters, materials, house, props, lights
src/scene3d/shots.py            the 11 shots (staging, acting, cameras)
src/compose/compose.py          compositor: transitions, rain, sparkles, captions, cards, CTA, encode
render_all.sh                   renders all shots with Blender (bpy)
```

## Re-rendering

Requirements: Python 3.13, `pip install bpy==5.2.2 numpy pillow`, ffmpeg, and the Inter font (`/usr/share/fonts/opentype/inter`).

```bash
python3.13 -m venv venv && ./venv/bin/pip install bpy==5.2.2 numpy pillow
PY=./venv/bin/python ./render_all.sh 50 10       # 3D renders -> renders/<shot>/  (~2.5 h on 4 CPU cores)
./venv/bin/python src/compose/compose.py         # -> output/sureshield_roofing_tiktok.mp4
./venv/bin/python src/compose/compose.py --stills 1.5,16.8,35.9   # review stills -> output/stills/
```

The 3D renders come out at 540×960 with 10 Cycles samples plus OpenImageDenoise. The compositor upscales them to 1080×1920 and draws all text and UI natively at 1080×1920, so typography stays sharp. For crisper 3D, render at a higher percentage, for example `./render_all.sh 100 16`. That takes about 4× longer. Slow shots (s2b, s5a, s6b, s7) render every second frame and the compositor blends the in-betweens.

To change caption timing, wording or highlights, edit `config/overlays.json` and re-run only the compositor.
