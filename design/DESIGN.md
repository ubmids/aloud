# aloud design spec

This file is binding. Every surface a judge or a viewer touches follows it:
the Vega app under `tv/`, the README, the Devpost gallery, the video cards,
the thumbnail, and any figure in `docs/`. If code and this file disagree, the
code is wrong or this file gets changed first, on purpose.

Status: **Signal is the chosen direction** (picked by Subomi, 15 October
2026). Its tokens below are binding; Liner notes and Meter in
`design/directions.html` are a record of what was considered, not options.

Judging context: Amazon "Build, Ship, Shape", Fire TV track, due Friday
23 October 2026, 12:00 PDT. Design is one of four equal criteria, worded as
"a complete, coherent product experience ... intuitive for the target device".
Judges may score from the description, images and video alone, so the gallery
and the video are the product as far as most judges know.

## Who it is for

Blind and low-vision viewers, and the people on the sofa with them. Many
low-vision viewers sit closer to the set, use high contrast and large text,
and read word shapes rather than letters. Many blind viewers never look at the
screen at all, so the screen is for the family, for low vision, and for the
judge. Design for a capable adult choosing a film, not a patient being helped.

## Principles (each one is testable)

1. **Audio leads, the picture confirms.** Every state on screen has a spoken
   form, and every spoken clip has the same words on screen. Test: each
   focusable element has a `ui.json` clip or an `accessibilityLabel` whose
   words match its visible text; no information exists only as a graphic.
2. **Readable from three metres.** No text below 24 px at 1080p (the Android
   TV floor of 12 sp on a 960 by 540 canvas). Labels are sentence case, never
   tracked-out capitals, because capitals erase word shape. A description is
   set at 44 px or larger with at most 42 characters a line. Test: grep the
   theme for any size under 24 and any `letterSpacing` above 1 on words.
3. **Focus survives greyscale.** Focus changes at least three things at once:
   a 6 px frame, an inverted fill, and a lift of at most 1.04. Opacity alone
   or hue alone never marks focus. Test: a greyscale screenshot of every
   screen still shows, without doubt, which element has focus.
4. **The film is the largest thing on screen.** In the panel player the
   picture covers at least 40% of the screen (today it is about 15%); in full
   screen it covers all of it. Nothing on the player is louder than the
   picture. Test: measure the stage rectangle at 1920 by 1080.
5. **One colour means one thing.** The voice colour marks aloud speaking and
   nothing else: the live description, the voice block in a gap, the caption
   edge. Focus is marked by inversion to ink, not by the voice colour. Test:
   `palette.voice` appears only in Voice, Timeline, the caption and the
   thumbnail mark.
6. **The gap is the signature.** One graphic recurs everywhere: a dialogue bar
   with a silence cut out of it and a sentence fitted inside. It is the logo,
   the player strip, the thumbnail and every card. Its numbers are real track
   data, never decoration. Test: every gap drawn is generated from a track
   file, and the README figure matches the shipped counts.
7. **Respect, in pictures and in words.** No eyes, sunglasses, canes,
   guide dogs, hands on faces, braille as ornament, soft-focus stock, or
   "for the blind" badges. Copy speaks to a viewer ("watch", "film", "you")
   and never about a condition ("suffer", "impaired", "help them",
   "the visually impaired", "afflicted"). Test: grep the repo and the
   assets for that list.

## Reference board

| Product | Take | Avoid |
|---|---|---|
| Apple TV app (tvOS) | Focus as a physical lift; one hero, one row, nothing else competing | Parallax and glossy focus that only works if you can see it |
| BBC iPlayer | Audio description treated as a first-class filter and badge, not a buried setting | Dense category rails that are slow to hear |
| BBC Subtitle Guidelines | Caption box rules for full screen mode: solid backing, short lines, position stays put | Their 37 character line, too short for a description sentence |
| Prime Video on Fire TV | The platform's own D-pad grammar: left/right in a row, down to the next row, Back always works | Autoplaying trailers and ads in the hero |
| Netflix on TV | The title page states its audio description availability in plain metadata | Previews that start speaking over a screen reader |
| MUBI | Restraint: one film at a time, typography doing the work | Grey on grey metadata that fails at a distance |
| The Criterion Channel | Typographic authority and full credits, film treated as culture | Small serif metadata, ornament |
| Apple Podcasts transcripts | The line being heard is lit as it is spoken; the next line waits dimmed | Transcript text at phone size |
| Descript | Speech and silence drawn as material you can see and edit | Pro-tool density in a living room |
| Be My Eyes | Confident, adult, warm branding for a blind audience without pity | Charity tone and volunteer framing |
| Atkinson Hyperlegible (Braille Institute) | A typeface drawn for low vision: distinct I/l/1, open counters, wide spacing | Using it at body sizes only and leaving headings to a generic face |
| YouDescribe | The domain's prior art: a visible description timeline | Its dated web look and small text |

## Tokens (direction: Signal)

Colours are exact. Contrast is WCAG 2.x, computed with
`design/contrast.py`, not eyeballed. "Raised" is the panel surface.

### Dark (the TV, the video, the gallery)

| Token | Hex | Use | On ground | On raised |
|---|---|---|---|---|
| `ground` | `#0B0B0A` | the room | | |
| `raised` | `#171716` | panels, unfocused controls | | |
| `recess` | `#000000` | a silence; behind the film | | |
| `line` | `#3A3A37` | hairlines only, never text | 1.7 | |
| `ink` | `#F4F3EE` | words; the focus fill | 17.7 | 16.1 |
| `inkSoft` | `#C8C7C0` | secondary words | 11.6 | 10.6 |
| `inkMuted` | `#A3A29B` | the dimmest tone allowed to carry a word | 7.7 | 7.0 |
| `voice` | `#FFD23F` | aloud is speaking. Nothing else | 13.6 | 12.4 |
| `onVoice` | `#0B0B0A` | text on a voice fill | 13.6 on voice | |
| `dialogue` | `#63635F` | someone in the film is talking (fill) | 3.3 | |
| `alert` | `#FF8A7A` | "The film could not be played." | 8.6 | 7.8 |

Graphics: dialogue against a silence 3.3:1, voice against dialogue 4.2:1, so
the three timeline states are separate in greyscale (WCAG 1.4.11 needs 3:1).
The current app's dialogue against a silence is 1.9:1, which fails it.
Pure white is avoided: `#F4F3EE` keeps 17.7:1 and halates less for viewers
with astigmatism or cataracts.

### Light (README figures, Devpost text images, print)

| Token | Hex | On ground |
|---|---|---|
| `ground` | `#F7F6F1` | |
| `raised` | `#FFFFFF` | |
| `ink` | `#111110` | 17.5 |
| `inkSoft` | `#3B3B38` | 10.4 |
| `inkMuted` | `#5C5B56` | 6.3 |
| `voice` | `#FFD23F` | 1.3, so a voice fill on light **always** carries a 2 px `ink` outline |
| `voiceInk` | `#6B5200` | 6.9, voice-coloured words on light |
| `dialogue` | `#86857E` | 3.4 |
| `alert` | `#B3261E` | 6.0 |

### Type

- **Atkinson Hyperlegible Next** (Google Fonts, OFL) for every word. It was
  drawn by the Braille Institute for low-vision readers, which makes it the
  one typeface choice that is also an argument. Weights 400, 600, 800.
- **Atkinson Hyperlegible Mono** for timecodes and counts, tabular.
- On Vega the TTFs are bundled with the app (about 100 KB a weight). Verify
  custom font loading on the Virtual Device in Phase 2; if it fails, fall
  back to the system sans at the same scale and keep every other rule.

Scale, in px at 1920 by 1080 (multiply by `u()` in code):

| Role | Size / line | Weight | Notes |
|---|---|---|---|
| display | 80 / 84 | 800 | the focused film's title |
| title | 52 / 60 | 800 | player title, card headlines |
| cue | 46 / 60 | 600 | the description itself, max 42 characters a line |
| lead | 34 / 44 | 600 | setting values, tile titles |
| body | 28 / 40 | 400 | synopsis, help lines |
| label | 24 / 32 | 600 | labels, sentence case, no tracking |
| mono | 24 / 32 | 400 | timecodes, counts |

### Space, shape, motion

- Base unit 8. Steps: 8, 16, 24, 32, 48, 64, 96.
- Safe area: 96 px left and right, 54 px top and bottom (the Fire TV 5%
  overscan margin). Today the app uses 64 and 44; that is inside the crop.
- Radius: 0 for surfaces and focus frames, 4 for the gap blocks only. Square
  edges are part of the broadcast vernacular and stop the screen looking like
  a stack of cards.
- Borders: none on unfocused surfaces. Separation comes from `raised` against
  `ground`, not from outlines.
- Motion: focus 120 ms ease-out, scale 1.00 to 1.04. A cue enters in 200 ms
  (fade plus 16 px rise). Nothing loops, nothing pulses, no parallax.
  Movement never carries information on its own.

## Components and screens

| Item | File | State today | Spec |
|---|---|---|---|
| Wordmark | `Home.tsx`, `Player.tsx` | 34 px bold system text | Atkinson 800 lowercase "aloud" plus the gap mark (two dialogue bars, a yellow block between) |
| Feature (hero) | `Home.tsx` | bordered rounded card, model ID strings | no card: words on `ground`, picture bleeding right with a hard edge; provenance in words from the track's describer field, e.g. "Described ahead of time by Claude Haiku 4.5. Read by Kokoro." |
| Film tile | `FilmTile.tsx` | rounded card, 0.72 opacity when unfocused | square 16:9 picture, title under it; focus = 6 px ink frame, title bar inverts to ink, lift 1.04; unfocused stays at full opacity |
| Setting | `Toggle.tsx` | 400 px card with tracked caps label | compact block: label, value; help line shown only on focus; focus = inverted ink fill |
| Voice panel | `Voice.tsx` | card with rail, 38 px cue | no card: the cue in 46 px ink on `ground`, a 6 px voice bar at its left only while speaking |
| Gap strip | `Timeline.tsx` | 92 px track plus a full-width orange lens | 32 px strip under the film; the lens shrinks to one line of text under the strip ("5.0 s of description in 5.9 s of quiet") |
| Caption (full screen) | `Player.tsx` | translucent box, orange edge | solid `#000000` at 85%, 6 px voice edge, 46 px, bottom-left inside the safe area |
| Status | `Player.tsx` | dot plus tracked "PLAYING" | "Playing" / "Paused" in label size, with the play or pause glyph |
| Error | `Player.tsx` | muted text on the stage | `alert` colour, plain sentence, and what to do next |

Screens: the shelf; the player with the voice panel; the player in full
screen; the "again" state after Menu; the VoiceView state (help line changes);
the film-failed state.

## Submission assets

- **Thumbnail:** Devpost 3:2 (export 1500 by 1000), YouTube 16:9 (1280 by
  720). Black ground, the gap mark large, one real description in quotes,
  "aloud" and "Fire TV". Text readable at 320 px wide: no more than 9 words
  besides the wordmark. No eyes, no faces in distress.
- **Gallery images:** real Virtual Device screenshots at 1920 by 1080, never
  mockups presented as the app. Order: shelf, player speaking, full screen
  with caption, the gap strip close up, the evaluation figure. Each gets a one
  line caption in the Devpost field saying what is happening and what is heard.
- **README hero:** the player-speaking screenshot, then the one-line pitch.
  The schedule figure is regenerated in these tokens (today it uses blue for
  dialogue and states 46 descriptions; the shelf track now has 45).
- **Video cards:** 1920 by 1080, `ground` background, left-aligned on the
  96 px safe margin, Atkinson (not Avenir), headline 72 px 800, support 40 px.
  Lower thirds: a 6 px voice bar plus name and role, bottom-left, never over a
  face. End card: wordmark, gap mark, two URLs, credits at 28 px minimum.
- **Credits** for Blender films appear wherever their frames do.

## Do and don't

Do:
- Write sizes and colours only through `tv/src/theme.ts` tokens.
- Put words on solid ground, never on the picture.
- Say what a control does in its value and help line.
- Keep the voice colour for the voice.
- Check every screen in greyscale and at 1280 by 720.

Don't:
- Use tracked capitals, text under 24 px, or opacity-only focus.
- Wrap things in rounded bordered cards to make them look designed.
- Show model IDs, quantisation names or voice codes (`af_heart`) to viewers.
- Use emoji, eye or blindness iconography, or gradients.
- Let any graphic, including the lens bar, outshine the film.
- Put a number on screen that did not come from a track file.
