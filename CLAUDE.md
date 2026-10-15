# aloud

`design/DESIGN.md` is binding for every surface: the Vega app in `tv/`, the
README, gallery images, video cards and the thumbnail. Read it before changing
anything a viewer or a judge sees. `design/directions.html` shows the three
directions considered; `design/contrast.py` computes every contrast ratio.

The five rules most likely to be broken:

1. No text under 24 px at 1080p, and no tracked-out capitals. Labels are
   sentence case.
2. Focus changes frame, fill and scale together. Never opacity or hue alone.
3. The voice colour means "aloud is speaking" and nothing else. Focus is not
   voice coloured.
4. No rounded bordered cards to fake structure. Surfaces are square and
   separated by tone, inside the 96 by 54 px safe area.
5. Every number or gap drawn comes from a track file, and no viewer ever sees a
   model ID, quantisation or voice code.

Tests: `for t in tests/test_*.py; do python3 $t; done`, and in `tv/`,
`npx jest && node test/schedule.test.mjs`. Keep them green.
