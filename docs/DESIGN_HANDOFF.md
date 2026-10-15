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
4. **Gallery and README hero** land in `design/assets/gallery/` (Virtual Device
   screenshots of the restyled build). The README hero should be
   `design/assets/gallery/02-player.png`, above the one-line pitch.
