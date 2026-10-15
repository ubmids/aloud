# Design handoff notes

From the design agent to whoever owns the text files named below. Design does
not edit README, SUBMISSION, DEMO_SCRIPT or `docs/video/*`; it leaves notes
here instead. The binding spec is `design/DESIGN.md` (direction: Signal).

## Open

1. **README alt text for `docs/schedule.svg`** (README line ~97) still says
   "blue blocks are dialogue ... orange blocks are aloud's descriptions". The
   figure is now grey for dialogue and caption yellow for aloud (same lanes,
   same data). Suggested: "grey blocks are dialogue as the film's production
   stems hear it, yellow blocks are aloud's descriptions, and no yellow block
   sits under a grey one."
2. **`docs/schedule.svg` data is from the earlier track** (46 descriptions,
   2.9 minutes). Only its colours changed. Regenerate it against the
   production stems with `aloud/figure.py` (now in Signal colours) when the
   shipped Tears of Steel track is final.
3. **Video cards.** `design/assets/` has the Signal versions, rendered from
   `design/assets/src/cards.html` with `design/assets/src/render.sh`. Same
   names as `docs/video/render.py` produced (`card-01-picture-off.png` to
   `card-06-end.png`), plus `lower-third.png`, `caption.png`, and
   `thumbnail-3x2.png` / `thumbnail-16x9.png`. A named lower third:
   `design/assets/src/render.sh lower-third "First name" "Low vision"`.
   Please point `docs/video/SHOTS.md` and the cut at these, and retire the
   Avenir cards in `render.py` (or make `render.py cards` copy from
   `design/assets/`).
4. **Gallery and README hero** are in `design/assets/gallery/`:
   `01-shelf.png`, `02-player.png` (a description being spoken at 1:12),
   `03-fullscreen.png` (the caption for the rest of the sofa) and
   `04-strip.png` (the schedule strip, close up). The README hero is
   `design/assets/readme-hero.png` (same as `02-player.png`); put it above the
   one-line pitch. These are pixel-faithful HTML renders of the committed
   Signal styles, using the real posters and real Tears of Steel frames inside
   the matching cue windows, because the Mac was too loaded to keep the VVD up.
   When `docs/video/record.py` re-records on the Signal build, take device
   stills at the same moments (shelf with Tears of Steel focused; player at
   1:12; full screen at 7:14) and drop them in under the same names. The
   gallery captions in Devpost should not say "screenshot" until then.
   Before: `design/assets/before/shelf-vvd.png` (the old look, from the VVD).
