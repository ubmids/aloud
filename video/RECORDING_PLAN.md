# aloud: recording plan for tonight (Tue 20 Oct)

## What was broken or missing (checked 20 Oct, 11:00 to 13:00 WAT)

| # | Problem | Status |
|---|---|---|
| 1 | `docs/video/assets/03-player.mp4` (the player shot: description, narration off, Menu repeats) was **never rendered**. The script needed it at 0:45. | **Fixed today.** Recorded on the Vega Virtual Device with `docs/video/record.py --only player`. Its plan is committed as `docs/video/plans/03-player.json`. |
| 2 | "Menu repeats the last description" had never been seen on the device. | **Seen today.** After Menu the player shows "Paused" and says "A hand holds an open newspaper." again. Still: `video/shots/vvd-menu-repeat-check.png`. |
| 3 | The old plan needed an editor (iMovie or similar) and about 2 hours of cutting by hand. | **Fixed today.** New `docs/video/cut.py` builds the whole video in about 45 s. A complete **captions-only** version (no voice, no face) is already rendered: `~/Desktop/hackathons/aloud-video/aloud-demo.mp4`, 2:48. |
| 4 | No blind or low-vision viewer was filmed. | The cut leaves that segment out and claims nothing about blind testers. If a consented `viewer.mp4` turns up later, drop it in `inserts/` and re-run. |
| 5 | At about 1:17 in the cut, aloud says "A human brain sits on a white platform..." while the screen has already moved to the "Tears of Steel" title. The description fills the quiet right after the brain shot. | It's how the track was timed, so judges may notice. Not fixed tonight. If it bothers you, it's one line in `tv/src/data/films/tears-of-steel.json`, but that means a rebuild and a new recording. |
| 6 | `tests/test_real_audio.py`: "recovered 10.3s of 10.0s" fails on this Mac. | Before today, and unrelated to the video: it synthesises speech with macOS `say`, whose timing changed on this macOS. The stricter test in the same file, "no gap ever overlaps dialogue", passes. All other test files pass. |
| 7 | Office hours question (is the Blender film footage acceptable?) | Unknown whether it was asked on 19 Oct. The footage is CC BY and credited on the end card. Keep it. |

## The facts

- **Event:** Build, Ship, Shape, Amazon Developer Hackathon (Devpost), Fire TV track (plus the Open Source mini).
- **Deadline:** Fri 23 Oct 2026, 12:00 PDT, which is **20:00 Lagos time (WAT)**. Plan to submit Thu 22 Oct.
- **Video rules (official rules page, checked 20 Oct):**
  - Under 3 minutes.
  - "Must show the project running on an actual Fire TV device or the Fire TV/Vega simulator." Every app shot here is the Vega Virtual Device.
  - Public on YouTube or Vimeo, in English.
  - No unlicensed music or trademarks.
  - **No voiceover or face is required.**
- **Length now:** 2:48 captions-only. With your voice it'll be about 2:30, because speech is quicker than reading time. The cut prints the total.

## The story in 3 beats

1. **Problem (0:00 to 0:37).**
   - Black screen, the film's sound, and aloud describing a flying ship you can't see. Then the picture fades up on exactly that.
   - Most of us watch TV without looking half the time, and some people never can.
2. **Demo (0:37 to 1:49).**
   - The shelf reads every title out loud.
   - In the player, a description drops into a gap and the film dips under it.
   - Narration off, then Menu repeats the last line.
3. **Why it matters (1:49 to end).**
   - It's made ahead of time and measured to fit the silence, so the TV does no AI work.
   - It's a library any Vega app can use.
   - "Look away, close your eyes, or never see the screen at all."

## Shot list (all pre-rendered, nothing to click)

Taken from today's captions-only cut. Stills in `video/shots/` (not in git).

| time | segment | on screen | sound | YOU |
|---|---|---|---|---|
| 0:00 | cold | Black, "Tears of Steel, with the picture off." Then the VVD full-screen picture fades up on the flying ship in a rifle scope. | Film plus aloud's two descriptions | nothing |
| 0:20 | who | aloud title card over a blurred shelf | `n-who` | voice memo, or face (`oncam-who.mov`) |
| 0:30 | everyone | "Cooking. Ironing. A toddler on your lap..." card | `n-everyone` | voice memo |
| 0:37 | shelf-intro | Still of the VVD shelf | `n-shelf` | voice memo |
| 0:46 | shelf | VVD shelf: right, right, left. Sintel and Big Buck Bunny read out. | the app | nothing |
| 1:08 | player | VVD player with voice panel: two descriptions with the dip, Narration off, Menu pauses and repeats | the app, then `n-player` at +23 s | voice memo |
| 1:49 | how | "Ahead of time, not live." card | `n-how` | voice memo |
| 2:09 | new | Full-screen picture, the flying ship | `n-new` | voice memo |
| 2:29 | library | "Any Vega app can play a described track." | `n-library` | voice memo |
| 2:36 | close | End card: github.com/ubmids/aloud and the film credits | `n-close` | voice memo, or face (`oncam-close.mov`) |

## Setup checklist (5 minutes)

- [ ] **Do Not Disturb on**, on both the phone and the Mac.
- [ ] A quiet room. Fan and AC off. Curtains and a bed soak up echo.
- [ ] **Phone: Voice Memos.**
  - Settings, Voice Memos, Audio Quality: **Lossless**.
  - Phone about 20 cm away, just below your mouth.
- [ ] The inserts folder exists: `~/Desktop/hackathons/aloud-video/inserts/`.
- [ ] Disk: about 7 GB free. The cut needs about 200 MB. Fine.

No Virtual Device, no build and no test account needed tonight: the device
footage is already recorded. The VVD was stopped after today's recording.

## Do this, in order (about 25 minutes)

1. **Record 8 voice memos** from SCRIPT.md. Keep each one short.
   - Trim the silence at both ends in Voice Memos (..., Edit Recording, Trim).
   - Rename them exactly: `n-who`, `n-everyone`, `n-shelf`, `n-player`, `n-how`, `n-new`, `n-library`, `n-close`.
   - `n-player` must be **under 8 seconds**, because it plays while narration is off and before Menu speaks.
2. **AirDrop to the Mac** and move them into `~/Desktop/hackathons/aloud-video/inserts/`.
3. **Optional faces:** `oncam-who.mov` (6 s, the who line) and `oncam-close.mov` (6 s, the close line), landscape. Each replaces its card. Skipping them is fine.
4. **Build:**
   ```bash
   cd ~/Desktop/hackathons/aloud && python3 docs/video/cut.py
   ```
   - It prints each segment and whether its line is `voice` or `caption`, then the total.
   - Any line you didn't record stays as a caption. That's fine.
5. **Watch once:** `open ~/Desktop/hackathons/aloud-video/aloud-demo.mp4`. Bad line? Re-record that memo, replace it, re-run step 4.
6. **Upload (by Thu):**
   - YouTube, Public. Title: "aloud: a Fire TV that tells you what's on screen, in the gaps between the dialogue".
   - Description: the one-line pitch, github.com/ubmids/aloud, and the credits from `docs/SUBMISSION.md` ("Credits and licences").
   - Subtitles: upload `aloud-demo.srt` (the voiceover lines).
   - Thumbnail: `docs/video/assets/thumbnail-16x9.png`.

## If something breaks

- **cut.py errors:** upload the captions-only `aloud-demo.mp4` that's already there. Rename it first (e.g. `aloud-demo-captions.mp4`) so a re-run can't overwrite it.
- **A memo sounds wrong or is the wrong length:** delete it from `inserts/`. That line goes back to a caption.
- **`n-player` is long and talks over the Menu repeat:** re-record it faster, or delete it.
- **Over 2:59:** only possible with long face clips. Trim them to 6 s.
- **The assets folder got wiped** (it's gitignored): rebuild with the commands in `docs/video/SHOTS.md`. The film is at `~/Desktop/hackathons/farm-outputs/023-hack-aloud-1st/out/films/tos/tears_of_steel_720p.mov`.

## Recording tools on this Mac

- **Voice:**
  - iPhone Voice Memos, then AirDrop.
  - Or QuickTime Player, File, New Audio Recording, then Export As, Audio Only.
- **Face:** iPhone camera, 1080p, landscape, eye level, window in front of you.
- **No screen recording is needed.** The Virtual Device footage is captured through the emulator console (`docs/video/SHOTS.md`), not Cmd+Shift+5.
- **Size:** about 40 to 60 MB, H.264 1080p. YouTube takes it directly.
