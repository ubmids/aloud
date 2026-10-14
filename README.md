# aloud

**Films that describe themselves, on Fire TV.**

Pick a film with the remote and aloud reads each title to you as you move
across the shelf. Press play, and in the silences between the lines a voice
tells you what is on screen: *"Through a circular viewport, a large, steampunk-style airship hovers above a cityscape."*
Never over a captioned line: on Tears of Steel the whole track overlaps
dialogue by 0.9 seconds in 12 minutes, measured against the film's production
stems. Close your eyes and you can still follow the film.

aloud is a Vega OS app (React Native for Vega) with a computer-vision pipeline
behind it. Before a film is ever played, a scheduler finds the silences in the
dialogue, a vision-language model looks at each silence where the picture has
changed and writes a sentence sized to it, each sentence is spoken and measured
into its gap, and the result ships as a timed description track. The app plays it as
a second voice, ducking the film a little while it speaks.

## Who it is for

Audio description, the narration track that makes a film followable without
the picture, exists for a small slice of what is on television, because a
human describer writes it by hand, title by title. In the US the rule
(47 CFR §79.3) asks the big four networks' stations in the largest markets, and
the top five cable networks, for **87.5 hours of description a quarter**: about
4% of a channel's airtime. Everything else is voluntary, so streaming
catalogues, FAST channels, independent and archive film mostly have none.

That matters first to blind and partially sighted viewers (the WHO counts at
least 2.2 billion people with some form of vision impairment). It also matters
to anyone watching without looking: cooking, ironing, a parent half-watching
with a child, an older viewer whose eyesight is going, someone following a film
in their second language. aloud is a way of watching with your ears.

## What a viewer does

1. **The shelf speaks.** Each title is read aloud as it takes focus, in the
   same voice that will describe the film: *"Tears of Steel. Science fiction,
   2012, 12 minutes. 45 descriptions."* Every setting does the same, on the
   shelf and under the film: *"Voice level, loud. The film drops well back, so
   every word is clear."* when it takes focus, and its new value when select
   changes it. If VoiceView is on, aloud stays quiet and lets the screen
   reader read the same words.
2. **Select plays it, described.** The first description lands
   11.6 seconds in. The screen shows the schedule: the dialogue as a bar,
   the silences cut out of it, and each description sitting inside one.
   "Picture: Full screen" turns it into an ordinary television player for
   whoever else is watching: the film fills the screen, the description being
   said shows as a caption, and the controls fade until a key is pressed.
3. **Missed something? Press Menu.** The film pauses, aloud says the last
   description again, and the film carries on. It works with narration off
   too, so one viewer on the sofa hears the film as it was made and another
   asks what is on screen when they need to, with one button. On the lighter
   "only what changed most" setting, two presses in two minutes tell aloud it
   is leaving out too much: it goes back to saying everything, and the
   setting's help line says why.
4. **The remote does the rest.** Narration on or off, voice level (the film
   dips further under the voice as you turn it up), how much is said,
   play/pause, ten-second skips, and Back to the shelf on the same title.
   The player also asks Vega for media-control focus so that Alexa transport
   commands can reach it; that has not been seen working on a device yet, so
   treat voice transport as untested.

Four open films from the Blender Foundation are on the shelf: **Tears of
Steel** (12 min, 45 descriptions), **Sintel** (15 min, 47 descriptions), the
family comedy **Big Buck Bunny** (10 min, 48 descriptions, and not one word of
dialogue, so aloud narrates over the score) and the Sintel trailer.

## What makes it work

- **Real descriptions of real frames.** Every track on the shelf was written by
  Qwen3-VL 4B, an open vision-language model, running on a CPU through
  llama.cpp, with no key and no GPU. The same pipeline can take Gemini or any
  OpenAI-compatible model with one environment variable (both are unit-tested
  against mocked APIs; no shipped track was written by them)
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
- **It stays out of the dialogue, and measures how well.** Each description
  is synthesised and measured before it is placed, and the track refuses to be
  written if any cue would leave its gap. Measured against the production
  stems, the shipped Tears of Steel track touches dialogue for **0.9 seconds**
  in 2.8 minutes of narration: five touches of under 0.4 s each, none of them
  on a captioned line. Two fall in the battle with no caption near them
  (uncaptioned shouts, or effects the two masters mix differently).

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

## What sets aloud apart

- **A native Vega app, not a web page.** React Native for Vega end to end: the
  film plays through `w3cmedia`'s `Video`, and every description through a
  second `AudioPlayer` that Vega is told is accessibility speech, so the
  platform can tell the voice from the film it describes.
- **A safety number anyone can reproduce.** Overlap with dialogue is measured
  against the film's own production stems, not against the detector that
  placed the cues: `python3 -m aloud.evaluate` on Tears of Steel gives 0.9
  seconds in 12 minutes, and an independent re-run from fresh downloads got
  the same figure.
- **An open model on an ordinary CPU.** Every shipped track was written by
  Qwen3-VL 4B through llama.cpp, with no key, no GPU and no per-title cloud
  bill (timings under "Where it goes"), so describing a back catalogue costs
  electricity.
- **The whole app speaks.** Titles, every setting and every change you make to one are
  read out in the description voice, so the shelf, the settings and the film
  are one experience for someone who cannot see the screen. With VoiceView on,
  aloud steps aside.
- **A track a person can check, and a gate before it ships.** The output is
  standard WebVTT and JSON. Before a cue is spoken or published it must sit
  inside its gap, finish its sentence, and be about the picture rather than
  the camera; characters are named only from each title's cast list, as
  the film itself names them.
- **The playback half is a library.** `vega-described-track` gives any React
  Native for Vega player the same scheduler and accessibility voice, with a
  patch for Amazon's multi-TV app sample. (PENDING: Subomi makes
  github.com/ubmids/vega-described-track public; it is private today.)

## Where it goes

A described track is a small file made once per title, and costs the
television nothing to play. Measured on 14 October 2026 on a shared 24-core
Linux box with no GPU (8 threads for the model, other jobs running):
Sintel (15 minutes of film) took 33 minutes to describe and Big Buck Bunny
(10 minutes) 14, each with about 5 GB of memory for the model and the
pipeline together. That makes two paths to viewers:

- **The aloud app on the Fire TV Appstore**, with a shelf of open and
  public-domain film described out of the box: a catalogue a blind viewer
  can browse, set up and watch without help.
- **Tracks for catalogue owners.** FAST channels and independent distributors
  run the same pipeline on their own titles, review the track if they want a
  person to sign off, and ship it beside the film as standard WebVTT.

## Built with

- **Vega OS / React Native for Vega**: `@amazon-devices/react-native-kepler`,
  `@amazon-devices/react-native-w3cmedia` (`Video` for the film, `AudioPlayer`
  with `USAGE_ACCESSIBILITY` for the voice), `TVFocusGuideView` and
  `useTVEventHandler` for the remote, `BackHandler`, `AccessibilityInfo` for
  VoiceView, and a request for Kepler media-control focus (voice transport,
  untested on a device).
- **Vision**: Qwen3-VL 4B on llama.cpp (CPU) wrote every shipped track.
  Gemini and OpenAI-compatible endpoints are supported in code, untested
  against the live services.
- **Voice**: Kokoro 82M on CPU (macOS `say` also supported).
- **Listening**: a hand-built speech-band and syllable-rhythm detector, Silero
  VAD, caption files.
- Python 3.12+, numpy, ffmpeg. 168 Python tests, 80
  JavaScript tests (57 Jest, 23 scheduler).

## Run it

```bash
pip install -r requirements.txt               # includes httpx, which the describers use
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
- [docs/MAC_CHECKLIST.md](docs/MAC_CHECKLIST.md): building and checking on the Vega Virtual Device (macOS or Ubuntu)

## Credits

*Tears of Steel*: (CC) Blender Foundation, mango.blender.org, CC BY 3.0.
*Sintel* and its trailer: (c) copyright Blender Foundation, durian.blender.org,
CC BY 3.0. *Big Buck Bunny*: (c) copyright 2008, Blender Foundation,
www.bigbuckbunny.org, CC BY 3.0. Films from download.blender.org, re-encoded for the app package;
descriptions are added as a separate track and the films are otherwise
unchanged. Silero VAD (MIT), Kokoro (Apache 2.0), Qwen3-VL (Apache 2.0).
aloud itself is MIT licensed.
