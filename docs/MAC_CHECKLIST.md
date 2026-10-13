# On the Mac: build, install, and check the Fire TV app

The Vega SDK and the Vega Virtual Device run on the Mac. Everything else was
built and checked on Linux: the TypeScript compiles, the Jest suites pass, and
`react-native build-vega` gets as far as the Hermes bundle before stopping at
"Vega CLI was not found", which is the native packaging step and the only one
that needs the SDK. So the code is known to compile; what is listed here is
what can only be seen on the device.

Work through it in order. Each step says what to look for and what to do if it
is not there.

## 1. Get the films into the package (once, about 15 minutes)

```bash
git checkout first-place && git pull
pip install -r requirements.txt
python3 -m aloud.films fetch          # Tears of Steel and Sintel, from download.blender.org
ls -la tv/assets/films/*/film.mp4     # three files: ~45MB, ~60MB, and the 1.9MB trailer
```

The trailer is in the repository; the two full films are not (too large for
git) and must be fetched before building, or those two titles will show
"The film could not be played."

## 2. Build and install

```bash
cd tv
export PATH="$HOME/vega/bin:$PATH"
npm install --fetch-timeout=1800000 --fetch-retries=5
npx tsc --noEmit && npx jest && node test/schedule.test.mjs
npm run build
vega virtual-device start
vega run-app build/aarch64-release/aloud_aarch64.vpkg
```

If the package is rejected for size, drop the trailer from `FILMS` in
`tv/src/catalogue.ts` first; if still too big, re-run `fetch` after lowering
`-crf 25` to `-crf 28` in `aloud/films.py`.

## 3. The shelf (home screen)

- [ ] It opens on the shelf, not on a film. **Tears of Steel** has focus (orange
      ring, lifted, "PRESS SELECT TO PLAY").
- [ ] **You hear the title read aloud** on launch focus: "Tears of Steel.
      Science fiction, 2012, 12 minutes. N descriptions." If silent: check the
      device log for the `AudioPlayer` initialising; it must happen before the
      first focus event. If it is a race, the fix is to call `announce` once
      `speaker.available` turns true.
- [ ] D-pad right moves to Sintel, then the trailer; each is read aloud, and
      each press cuts off the previous announcement rather than queuing.
- [ ] The big panel updates with each focus: poster, genre/year/minutes,
      synopsis, "N descriptions, M minutes of narration", the describer and
      voice line, and the credit.
- [ ] D-pad down reaches the three settings; up returns to the row. If down
      does nothing, wrap the two `TVFocusGuideView`s' `autoFocus` in
      `destinations` (see `Home.tsx`).
- [ ] "Read the menu aloud" Off stops the announcements. With VoiceView on
      (Settings > Accessibility), the app stays quiet and VoiceView reads the
      tile label instead; the help line says so.

## 4. The player

- [ ] Select on Tears of Steel plays the film with the schedule strip, the
      voice panel and the controls.
- [ ] **The first description is heard inside the first 20 seconds** (about
      11.5s: the engines firing). This is the hero moment of the video.
- [ ] Descriptions never start over a line of dialogue. Watch the strip: lit
      blocks only ever sit in the recesses.
- [ ] While a description plays, the film dips (Normal level) and comes back
      when it ends. "Voice level" cycles Quiet / Normal / Loud and the dip is
      audibly smaller / larger. If the film never dips, `HTMLVideoElement.volume`
      may be read-only on this build: log it to the friction log.
- [ ] "Narration" Off silences descriptions immediately; On resumes from the
      next gap without repeating the ones already said.
- [ ] Play/pause on the remote pauses film and description together.
- [ ] **Menu (the ≡ button) says the last description again.** The film
      pauses, the voice panel lights the repeated sentence, and the film resumes
      on its own about half a second after the voice stops. Try it with
      Narration Off as well: it must still speak. Try it while paused: it speaks
      and the film stays paused. If nothing happens, add
      `console.log(e.eventType)` at the top of `remote` in `Player.tsx`, press
      the button, and put whatever name the device reports next to `'menu'` in
      the `switch`.
- [ ] Rewind / fast-forward (or skip) moves 10 seconds; a description that
      was skipped over does not fire late, and one rewound past fires again.
- [ ] **Back returns to the shelf with the same title focused**, and nothing
      keeps talking.
- [ ] Voice: with the simulator's Alexa voice input, try "Alexa, pause" and
      "Alexa, resume". The player calls `setMediaControlFocus` once metadata
      loads. If this does not work on the Virtual Device, say so in the video
      ("remote and voice on a real Fire TV"), and log it in the friction log;
      do not show it if it does not work.

## 5. Recording

Use the Virtual Device window at 1920x1080. Record system audio (the
descriptions are the product). See `docs/DEMO_SCRIPT.md` for the shot list.

## If something is broken and there is no time

- The trailer alone is a complete demo: it is bundled, its track is real, and
  it needs no fetch.
- `git log --oneline master..first-place` lists every change on this branch;
  `master` still has the version verified on 17 September.
