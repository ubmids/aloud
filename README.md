# aloud

**Films that describe themselves, on Fire TV.**

Pick a film with the remote and aloud reads each title to you as you move
across the shelf. Press play, and in every silence between the lines a voice
tells you what is on screen: *"Through a circular viewport, a large, steampunk-style airship hovers above a cityscape."*
Never over a line of dialogue. Close your eyes and you can still follow the
film.

aloud is a Vega OS app (React Native for Vega) with a computer-vision pipeline
behind it. Before a film is ever played, a vision-language model watches each
new shot, a scheduler finds the silences in the dialogue and measures what fits
in them, and the result ships as a timed description track. The app plays it as
a second voice, ducking the film a little while it speaks.

## Who it is for

Audio description, the narration track that makes a film followable without
the picture, exists for a small slice of what is on television, because a
human describer writes it by hand, title by title. In the US the broadcast
rules only require it from the largest networks, for a fixed number of hours a
quarter. Streaming catalogues, FAST channels, independent and archive film
mostly have none.

That matters first to blind and partially sighted viewers (the WHO counts at
least 2.2 billion people with some form of vision impairment). It also matters
to anyone watching without looking: cooking, ironing, a parent half-watching
with a child, an older viewer whose eyesight is going, someone following a film
in their second language. aloud is a way of watching with your ears.

## What a viewer does

1. **The shelf speaks.** Each title is read aloud as it takes focus, in the
   same voice that will describe the film: *"Tears of Steel. Science fiction,
   2012, 12 minutes. 34 descriptions."* If VoiceView is on, aloud
   stays quiet and lets the screen reader read the same words.
2. **Select plays it, described.** The first description lands
   11.6 seconds in. The screen shows the schedule: the dialogue as a bar,
   the silences cut out of it, and each description sitting inside one.
3. **Missed something? Press Menu.** The film pauses, aloud says the last
   description again, and the film carries on. It works with narration off
   too, so one viewer on the sofa hears the film as it was made and another
   asks what is on screen when they need to, with one button.
4. **Remote and voice do the rest.** Narration on or off, voice level (the film
   dips further under the voice as you turn it up), how much is said,
   play/pause, ten-second skips, and Back to the shelf on the same title.
   Transport goes through Vega's media controls, so Alexa voice commands reach
   the same player.

Three open films from the Blender Foundation are on the shelf: **Tears of
Steel** (12 min, 34 descriptions), **Sintel** (15 min,
47 descriptions) and the Sintel trailer.

## What makes it work

- **Real descriptions of real frames.** Every track on the shelf was written by
  Qwen3-VL 4B, an open vision-language model, running on a CPU through
  llama.cpp, with no key and no GPU. The same pipeline takes Gemini or any
  OpenAI-compatible model with one environment variable
  ([docs/DESCRIBERS.md](docs/DESCRIBERS.md)). The describer sees two frames of
  each shot so it can describe action, and what it said last so it says what
  is new; on-screen text is read out ("On screen: 40 YEARS LATER.").
- **It finds speech, not silence.** Two independent detectors listen for
  dialogue (a hand-built speech-rhythm detector and the Silero neural voice
  detector) and the title's own caption file is read as a third map. Measured
  on Tears of Steel against a dialogue map built from the film's production
  stems, the hand-built detector alone left **27.4 seconds** of dialogue inside
  its "gaps"; all three together leave **0.9 seconds**
  ([docs/EVALUATION.md](docs/EVALUATION.md)).
- **It never talks over a line.** Each description is synthesised and measured
  before it is placed, and the track refuses to be written if any cue would
  leave its gap. Measured the same way, the shipped Tears of Steel track speaks
  **0.6 seconds** over dialogue in 2.6 minutes of narration.

  ![Tears of Steel in four-minute rows: blue blocks are dialogue as the film's
  production stems hear it, orange blocks are aloud's descriptions, and no
  orange block sits under a blue one.](docs/schedule.svg)
- **It knows when to be quiet.** A gap gets a description only if the picture
  changed since the last one; long action sequences are split at hard cuts so a
  forty-second battle gets more than one sentence; black frames and sentences
  about the film rather than of it ("Text appears on screen.") are refused.

## How this differs from Prime Video's AI audio description

Prime Video uses AI to find the gaps in the dialogue so that its production
teams can write description scripts faster, for its own catalogue. That keeps a
person writing every line, which is the cost that leaves most film undescribed.
aloud writes the description itself, places it, and plays it on the device, so
it reaches the titles nobody will pay a describer for. And because the output
is a standard timed track (WebVTT and JSON) made **ahead of time, not live**, a
person can still review or correct it before it airs, and the device does no
inference at all.

## Where it goes

A described track is a small file made once per title: Tears of Steel took
about twenty minutes on one ordinary CPU with an open model, and costs
the television nothing to play. That makes two paths to viewers:

- **The aloud app on the Fire TV Appstore**, with a shelf of open and
  public-domain film described out of the box, the first catalogue a blind
  viewer can browse and watch without help.
- **Tracks for catalogue owners.** FAST channels and independent distributors
  run the same pipeline on their own titles, review the track if they want a
  person to sign off, and ship it beside the film as standard WebVTT.

## Built with

- **Vega OS / React Native for Vega**: `@amazon-devices/react-native-kepler`,
  `@amazon-devices/react-native-w3cmedia` (`Video` for the film, `AudioPlayer`
  with `USAGE_ACCESSIBILITY` for the voice), `TVFocusGuideView` and
  `useTVEventHandler` for the remote, Kepler media controls for voice
  transport, `BackHandler`, `AccessibilityInfo` for VoiceView.
- **Vision**: Qwen3-VL 4B on llama.cpp (CPU), or Gemini, or any
  OpenAI-compatible endpoint.
- **Voice**: Kokoro 82M on CPU (macOS `say` also supported).
- **Listening**: a hand-built speech-band and syllable-rhythm detector, Silero
  VAD, caption files.
- Python 3.12+, numpy, ffmpeg. 150 Python tests, 52
  JavaScript tests.

## Run it

```bash
pip install -r requirements.txt
export ALOUD_LOCAL_VLM_URL=http://127.0.0.1:8181/v1   # or GEMINI_API_KEY=..., see docs/DESCRIBERS.md
python3 -m aloud film.mp4 --captions film.srt --out out/
```

Writes `out/description.vtt`, `out/description.json`, and `out/described.mp4`,
the film with its descriptions mixed in. Play that one with your eyes shut.

Everything on the shelf, rebuilt from the Blender mirror:

```bash
python3 -m aloud.films build    # fetch, describe, publish into tv/
cd tv && npm install && npm run build
vega virtual-device start && vega run-app build/aarch64-release/aloud_aarch64.vpkg
```

Tests: `for t in tests/test_*.py; do python3 $t; done`, and in `tv/`,
`npx jest && node test/schedule.test.mjs`.

## More

- [docs/EVALUATION.md](docs/EVALUATION.md): how the no-overlap claim is measured
- [docs/DESCRIBERS.md](docs/DESCRIBERS.md): providers, the local model, regenerating
- [docs/FRICTION_LOG.md](docs/FRICTION_LOG.md): building a media app on Vega OS
- [docs/ENGINEERING.md](docs/ENGINEERING.md): the build notebook, calibration, mutation testing
- [docs/MAC_CHECKLIST.md](docs/MAC_CHECKLIST.md): building and checking on the Vega Virtual Device

## Credits

*Tears of Steel*: (CC) Blender Foundation, mango.blender.org, CC BY 3.0.
*Sintel* and its trailer: (c) copyright Blender Foundation, durian.blender.org,
CC BY 3.0. Films from download.blender.org, re-encoded for the app package;
descriptions are added as a separate track and the films are otherwise
unchanged. Silero VAD (MIT), Kokoro (Apache 2.0), Qwen3-VL (Apache 2.0).
aloud itself is MIT licensed.
