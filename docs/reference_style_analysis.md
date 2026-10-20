# Reference style analysis: Oct-20Footage1

I downloaded the reference from the GitHub release
(`Fottage1/Oct-20Footage1`, 14.2 MB). It is H.264 + AAC, 1080×1920, 30 fps,
19.0 s long. I watched it in full, extracted frames at 2 fps and built a
1 fps contact sheet. These are the observations the ad was built against.

## Rendering and characters
- A soft, Pixar-like **3D toy look**. Forms are chunky and rounded-block
  (the head is a big bevelled cube), the materials are tactile (knitted
  beanie, fleece hoodie, glossy clay tile), there is subsurface-style skin,
  and the eyes are big, glossy and lit with specular highlights.
- The character has a big head and a small body. Expressions come from the
  brows, eye direction and a small mouth. Poses are simple and readable:
  hand on chin while worrying, holding a phone, looking up.
- A second "mascot" character (a cute roof tile with a face, stubby arms
  and legs, blush and a wink) carries the CTA.

## Lighting and palette
- The scenes are low-key and at night. The ambient is deep navy
  (≈ RGB 4–8, 4–10, 16–22) with warm practical lights: lit windows, city
  bokeh and street lamps. A rim light separates the character from the
  background, there is shallow depth of field, and there is rain.
- Orange is the accent hue. It is used in the caption highlights, the card
  accent bars and the beanie. Red (≈ 217,56,47) marks the "worst" item.
  Green (a WhatsApp-style pill) is used for the action button.

## Captions
- **White Inter-style bold sans** at about 68 px on a 1080-wide frame. The
  text is in sentence case, left-aligned at x≈66, sits near the top
  (y≈150) and wraps onto at most two lines.
- Captions follow the **spoken words**. They are revealed word by word in
  time with the VO, with a quick fade/rise (a word mid-fade appears grey).
- Key words are **orange (≈ 248,100,39) with a thick rounded orange
  underline**, e.g. "leaking.", "quotes.", "truth?", "photo.", "wrong.".
- The captions stay sharp during the motion-blur transitions while
  everything else blurs.

## Cards and UI
- **Cream rounded cards** (≈ 247,242,235, radius ≈ 26 px) with soft drop
  shadows. Each card has a coloured left accent bar (orange, orange, then
  red for the worst), a numbered beige circle, a bold title and a grey
  subtitle. Cards stack vertically under the caption.
- Each card enters on its own word: a short upward move, a fade and a
  slight scale settle. Once in place the cards hover gently, out of phase
  with each other.
- Other panels: a dark chat panel holding a photo, and a "ROOF REPORT"
  card with a green "FREE" badge, a photo, orange circle annotations and
  an orange pill with a check icon.
- The CTA screen has a small white line above a **green rounded pill
  button**, plus sparkles and a swirling sparkle trail around the mascot.

## Camera and transitions
- The camera moves slowly: push-ins, slight pans and close-ups. Everything
  is framed for vertical viewing, with the character in the lower half and
  the text and cards in the upper half.
- Cuts use **strong horizontal directional motion blur** (whip pans). The
  scene layer and cards slide and blur while the caption stays crisp.
  There is also a blur dissolve into the final mascot scene.
- Warm floating bokeh and star particles appear in the final scene.

## How the Fenland ad applies this
| Reference trait | Fenland ad |
|---|---|
| 3D toy characters, rounded-block heads | Original cast built procedurally in Blender (Cycles). **Tom** the homeowner has a chestnut quiff, a green knit jumper with a white collar and jeans, and wears no hat or glasses. **Lawrence** has a navy cap, a beard and a hi-vis vest. A ginger-haired crew member completes the team. |
| Tile mascot for the CTA | An original **block-paver mascot** with a face, blush, a wink and waving arms |
| Night, navy and warm practicals | Rainy night for the "problem" scenes, a warm blue-hour dusk for the "solution" scenes |
| Word-by-word captions with orange underlines | The same treatment, using the verbatim VO and real word timestamps |
| Cream stacked cards | Risk cards (orange, orange, red), trust cards with green checks, a map card, a logo card, service chips, and a "PROJECT CHECK" card (after the reference's ROOF REPORT) |
| Whip-blur transitions, sharp captions | Horizontal, vertical and zoom whips plus blur dissolves, with captions composited after the blur |
| Green pill CTA and sparkles | A "GET YOUR FREE QUOTE" green pill, the phone number, the website, a sparkle swirl and bokeh |

## Known differences
The reference looks like a high-end (probably AI-assisted) 3D render. This
ad is made entirely in code (procedural geometry, Cycles CPU rendering at
540×960 with denoising, then upscaled ×2). Text, cards and the logo are
drawn natively at 1080×1920. As a result the characters are simpler and
the materials less detailed than the reference, even though the overall
visual language matches.
