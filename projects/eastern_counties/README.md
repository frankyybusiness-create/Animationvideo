# Eastern Counties Paving — 9:16 cartoon advert

Final video: `output/eastern_counties_paving_tiktok.mp4` (1080×1920, 30 fps, H.264 + AAC, 46.6 s)
Contact sheet: `output/eastern_counties_contact_sheet.jpg`

- **Voiceover:** `assets/voiceover.mp3` is the original recording, unedited, and it sets the timeline. It is 45.56 s long. The picture holds for 1 s after the last word so the call-to-action stays readable.
- **Business name:** the brief said "Easton County's Paving", but the voiceover says "Eastern County's Paving", and the logo and intake form say **Eastern Counties Paving**. The advert uses EASTERN COUNTIES PAVING.
- **No logo, contact details or offers:** the name appears as typography only. There is no phone number, website, price, date or slot count. The phone number and website from the intake form can be added to `cta` in `config/overlays.json` if wanted.

## Style source: Oct-20Footage1 only

This project uses the same visual system as the reference. The root `README.md` covers that analysis in full. In short:

- **Look:** 3D toy/clay characters, a navy night, a warm key light and a cool rim light, and shallow depth of field with bokeh.
- **Captions:** top-left, Inter Bold 80 px, words that rise in, and orange highlights with a drawn-on underline.
- **Cards and panels:** cream cards with an accent strip, tilt and hover. Report-style panels have a header, a pill and a badge.
- **Cuts:** whip-pans and defocus dissolves.
- **Final scene:** a green CTA pill with a glow, and gold sparkles.

**Characters:**
- **Linda**, the homeowner, is new. She has an auburn bob with a fringe, a cranberry knit jumper under a mustard quilted gilet, and no glasses.
- **The paving crew** are also new. They wear charcoal workwear, orange hi-vis vests and kneepads. One has a beard and a navy cap; the other has a fair crop.

## Scenes (times on the voiceover)

| Shot | Time (s) | Content | Overlays |
|---|---|---|---|
| e1 | 0.00–4.20 | Low glide over cracked, sunken, weedy block paving, then a tilt up to a worried Linda | **Cracks. Sinking. Wear.** |
| e2 | 4.20–8.40 | The damage worsens: blocks sink further and weeds grow. Linda flinches | Costly structural **damage.** |
| e3 | 8.40–10.80 | Wide street of Essex homes at dusk | Across **Essex.** + label "ESSEX & SURROUNDING AREAS" |
| e4 | 10.80–15.25 | The paving team meets Linda; tablet, mallet, thumbs-up | Name card + Built on **trust.** |
| e5 | 15.25–20.30 | Kneeling paver lays and taps new blocks | Cards: Transparent pricing / Elite craftsmanship / No hidden fees. Zero cut **corners.** |
| e6a | 20.30–23.10 | "Seasonal bookings" panel; slot tiles fill up (no dates or counts) | Seasonal slots **filling fast.** |
| e6b | 23.10–27.10 | Wind, falling leaves and darkening sky; crew working, Linda nods | Secure your **property.** / Before the **weather turns.** |
| e7a | 27.10–30.25 | New driveway sweeps into place row by row | Driveway **transformations.** |
| e7b | 30.25–31.45 | Patio slabs drop in | Patio **overhauls.** |
| e7c | 31.45–32.55 | Paver kneeling, precision tapping | Precision **repairs.** |
| e8 | 32.55–36.50 | Finished driveway; crew waves, Linda delighted | Our **local** team. / Handled with **care.** |
| e9 | 36.50–39.70 | "Paving check" panel showing the damaged-blocks close-up | Don't **wait** until it's too **late.** |
| e10 | 39.70–46.60 | Finished home; Linda waves; sparkles; CTA | Secure your **free quote.** / Lock in your **installation date.** + name, "Free, no-obligation quote", "Get your free quote" |

## Files

```
projects/eastern_counties/assets/voiceover.mp3
projects/eastern_counties/config/timeline.json        shot cut points (in speech gaps) + render step
projects/eastern_counties/config/overlays.json        captions, label, name card, cards, panels, CTA, rain, transitions
projects/eastern_counties/config/voiceover_words.json word-level alignment of the voiceover
projects/eastern_counties/render.sh                   renders every shot
src/scene3d/eastern.py                                the 13 shots
src/scene3d/lib.py                                    shared characters, paving builders, house, props
src/compose/compose.py                                shared compositor (--project selects the config)
```

## Rendering again

```bash
python3.13 -m venv venv && ./venv/bin/pip install bpy==5.2.2 numpy pillow
PY=./venv/bin/python projects/eastern_counties/render.sh 50 10            # about 2.5 h on 4 CPU cores
./venv/bin/python src/compose/compose.py --project projects/eastern_counties \
    --out output/eastern_counties_paving_tiktok.mp4
```

If you only change captions, cards or timing in `overlays.json`, re-run just the compositor (a few minutes).
