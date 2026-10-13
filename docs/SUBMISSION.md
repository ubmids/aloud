# Submission copy: aloud, Amazon "Build, Ship, Shape", Fire TV track

Deadline **Friday 23 October 2026, 12:00 PDT (19:00 UTC)**. Devpost:
amazonappdev2026. Paste the sections below into the matching Devpost fields.

Judged on four equal criteria (Tech Implementation, Design, Potential Impact,
Quality of the Idea; ties go to Tech), plus up to 10% for the friction log
(`docs/FRICTION_LOG.md`, 18 entries). Stage One: runs on Fire OS or Vega OS and
is shown on a Fire TV or the Vega simulator. The September version of aloud
(the single-film player, friction log entries 1 to 13) ran on the Vega Virtual
Device; **the current app has not yet been run on one** (PENDING: Subomi's VVD
run, see "Needs Subomi" below). No developer account or Appstore listing is
required by the rules.

Category fit, in the track's own words: **AI-enhanced viewing**, **computer
vision**, and **multi-modal UX combining voice, D-pad and visual in a single
flow**.

---

## Project name

aloud

## Elevator pitch (200 characters)

Films that describe themselves on Fire TV. In each silence between lines, a
voice tells you what a vision model saw on screen, measured to fit the gap.
Watch with your ears.

## Text description

### What it does

aloud is a Fire TV app, built on Vega OS, that lets you watch a film with your
ears. The shelf reads each title aloud as the remote moves across it. Press
play and, in every silence between the lines, a voice tells you what is on
screen: *"Through a circular viewport, a large, steampunk-style airship hovers above a cityscape."* Each description is measured into a silence (on
*Tears of Steel*, 0.9 seconds of overlap with dialogue in 12 minutes, none on a
captioned line), and the film dips a little under the voice so every word is
clear.

Missed a description, or watching with narration off beside someone who does
not need it? Press **Menu**: the film pauses, aloud says what is on screen, and
the film carries on. On the lighter "only what changed most" setting, two
presses in two minutes tell aloud it is leaving out too much, and it goes back
to saying everything and says why. Narration on or off, voice level, how much is said,
play/pause, skips and Back are all on the remote. (The player also requests
Vega media-control focus for Alexa transport; that is untested on a device, so
it is not shown.) One voice speaks the menu and the
film, so a viewer who cannot see the screen gets one continuous experience
rather than a menu and then a film.

### Who it is for

Audio description exists for a small slice of television because a person
writes it by hand, title by title. The US rule (47 CFR §79.3) requires 87.5
hours a quarter from the big four networks' stations in the largest markets and
the top five cable networks, about 4% of a channel's airtime; everything else,
including most streaming, is voluntary. It matters most to blind and partially
sighted viewers, and to a much larger audience watching without looking: the
cook, the parent half-watching, the older viewer whose eyesight is going, the
viewer following a film in a second language. aloud is aimed at the titles
nobody will pay a describer for: FAST channels, archives, independent film, and
the long tail of every catalogue.

### How it is different from Prime Video's AI

Prime Video uses AI to find the gaps in the dialogue so its production teams
can write description scripts faster, for its own catalogue. A person still
writes every line. aloud writes the description itself, places it, measures it
and plays it on the device. The track is made **ahead of time, not live**, as a
standard WebVTT/JSON file, so a person can still review it before it airs, and
the television does no inference at all.

### How it works

1. **Listen for speech, three ways.** A hand-built speech-band and
   syllable-rhythm detector, the Silero neural voice detector, and the title's
   own caption file. A gap must be clear of all three. On *Tears of Steel*,
   measured against a dialogue map built from the film's production stems, the
   hand-built detector alone left 27.4 seconds of dialogue inside its gaps; all
   three together leave 0.9.
2. **Describe what changed.** For each gap where the picture has changed, a
   vision-language model is shown two frames of the shot and the last three
   things said, and asked for one present-tense sentence of about the number of
   words the gap can hold. On-screen text is read out. Long action sequences
   are split at hard cuts. Black frames, and sentences about the film rather
   than of it, are refused.
3. **Measure, then place.** Each description is synthesised and measured, never
   estimated, and placed inside its gap. The track refuses to be written if any
   cue would leave its gap.
4. **Play it on Fire TV.** The Vega app plays the film through `w3cmedia`'s
   `Video`, fires each pre-synthesised cue through an `AudioPlayer` classified
   as accessibility speech, and decides from `currentTime` alone whether the
   rest of the gap can still hold it.

The tracks on the shelf were written by **Qwen3-VL 4B**, an open model, on a
CPU via llama.cpp, with no key and no GPU; the same pipeline takes Gemini or any
OpenAI-compatible model with one environment variable. *Tears of Steel* carries
46 descriptions (2.9 minutes of narration), of which
0.9 seconds overlap dialogue, measured against the production stems, in five
touches of under 0.4 s and none on a captioned line. *Sintel* carries 49 and
the family comedy *Big Buck Bunny*, which has no dialogue at all, 50.

### Challenges

- **Silence is not the absence of sound.** A film's quiet parts are full of
  score and rain; its loud parts are sometimes where the lines are. The detector
  that never failed on recorded voices over rain and music failed 30 times on a
  real film, which is why it now has two more ears.
- **Vega gives an app the time, four times a second, and nothing else.** No
  frames, no frame callbacks. So vision runs ahead of time and the player's
  scheduler refuses to start a description the rest of the gap can no longer
  hold.
- **Models write about the film instead of in it.** "Screen is completely
  black." "Text appears on screen." Both now leave the gap silent.

### What's next

A describer review screen for human sign-off; tracks served per title from a
catalogue service rather than bundled; describing a household's own library;
voices and languages per viewer.

## Built with

vega-os, react-native-for-vega, react-native-kepler, react-native-w3cmedia,
typescript, python, llama.cpp, qwen3-vl, kokoro-tts, silero-vad,
ffmpeg, numpy, jest

## Try it out

- Repository: https://github.com/ubmids/aloud (branch `first-place` until merged)
- Video: (YouTube link)

## Testing instructions (for judges)

The trailer plays straight from a clone. The three full films are too large
for git and are fetched from the Blender Foundation's mirror first; without
that step their tiles say "The film could not be played."

```bash
git clone https://github.com/ubmids/aloud && cd aloud
pip install -r requirements.txt
python3 -m aloud.films fetch          # Tears of Steel, Sintel, Big Buck Bunny (~15 min)
cd tv && npm ci && npm run build      # needs the Vega SDK on macOS or Ubuntu
vega virtual-device start
vega run-app build/<arch>-release/aloud_<arch>.vpkg   # x86_64 on an Intel/AMD host, aarch64 on Apple silicon
```

On the shelf, left/right moves between films (each is read aloud), down
reaches the settings (each says its name and value), select plays. In the
player: Menu repeats the last description; "Picture" switches to full screen.
Tests: `for t in tests/test_*.py; do python3 $t; done`, and in `tv/`,
`npx jest && node test/schedule.test.mjs`.

## Credits and licences (put in the video description too)

*Tears of Steel*, (CC) Blender Foundation, mango.blender.org. *Sintel* and its
trailer, (c) copyright Blender Foundation, durian.blender.org. *Big Buck
Bunny*, (c) copyright 2008, Blender Foundation, www.bigbuckbunny.org. All CC BY 3.0,
from download.blender.org, re-encoded; descriptions are a separate track.

---

## Product Feedback (REQUIRED FIELD)

> Every claim below is drawn from `docs/FRICTION_LOG.md`, which has full
> reproduction steps, severity and a suggested fix for each of its 18 entries.

### Which developer tools, APIs and SDKs did you use, and for what?

- **Vega SDK 0.24.9914** and the `vega` CLI, for build, virtual device and app
  install.
- **`@amazon-devices/react-native-kepler` 4.0** and **React Native 0.83** for
  the app.
- **`@amazon-devices/react-native-w3cmedia` 2.3** for video playback, and its
  `AudioPlayer` for speaking the description cues.
- **Vega Virtual Device** for verification, since it is what the rules accept
  in place of hardware.
- **`TVFocusGuideView`, `useTVEventHandler`, `BackHandler`,
  `AccessibilityInfo`** (all from `react-native-kepler`) for the remote-driven
  shelf and player, and Kepler media controls (`setMediaControlFocus`) for voice
  transport.
- The Kepler Jest preset with `@testing-library/react-native` for focus-state
  tests, and `react-native build-vega` on Linux for the JavaScript and Hermes
  stages.
- Python 3.12+ for the pipeline: gap detection, description, fitting, planning,
  track writing, mixing and evaluation, with Qwen3-VL 4B on llama.cpp (CPU),
  Kokoro 82M and Silero VAD.

### What worked well

The Vega Virtual Device is the strongest part of the toolchain. It boots in
under a minute, it needs no developer account, and `vega device install-app`
followed by `vega device running-apps` gives a clean, scriptable verification
loop. Being able to prove an app runs without owning the hardware is not
something every TV platform offers, and it is the reason this submission exists
at all.

The build itself is unfussy. `react-native build-vega --build-type Release`
produced a working `.vpkg` first time, for both aarch64 and armv7.

### What needs improvement

Eighteen entries, two of them critical. In rough order of cost:

1. **The manifest entries playback depends on are split across three pages that
   disagree with each other.** Severity critical. Nothing plays until it is
   fixed, and the page a developer is most likely to find first is not the one
   that is right.
2. **Every distinct media failure reports as the same error, with no detail.**
   Severity critical, and it is what turned each of the entries below into its
   own multi-hour investigation. One error string for a dozen root causes means
   the platform is telling you that something is wrong while withholding the
   only thing that would help.
3. **The `Video` component ignores `style` and sizes itself to NaN by default.**
   Silent, and the symptom appears three layers away from the cause.
4. **Setting `src` as a prop attaches the source before the surface exists.**
   The correct-looking code is the broken code, which is the worst possible
   shape for a bug.
5. **Bundled media cannot be referenced through `require`, and `file://` breaks
   it.**
6. **The platform never states that decoded frames are unavailable to app
   JavaScript.** This one is architectural rather than cosmetic: it decides
   whether on-device vision is possible at all, and a developer can spend days
   building toward something the platform will never permit before finding out.
7. **`AudioPlayer` fails silently if you skip `initialize()`.** No error,
   anywhere, at any layer.
8. **`vega project generate` overwrote `.gitignore`** on a repository destined
   to go public. A small bug with a security shape, and the one on this list I
   would fix first.
9. `npm install` of the Kepler package times out with no warning, which
   disproportionately affects developers on slower connections.
10. Enum member names are absent from the prose documentation.
11. The device shell cannot see the app's own package, so you cannot verify
    what actually shipped.
12. The `build_number is 0` warning does not say what it should be.
13. The media player documentation's first line of code imports from a package
    that does not exist.
14. `build-vega` builds the whole JavaScript and Hermes bundle before saying
    the SDK is missing, with no way to stop after the SDK-free stages for CI.
15. The method that routes Alexa and remote transport commands to a player,
    `setMediaControlFocus`, is marked `@hidden` in its own type definitions.
16. The remote event's doc comment and its type disagree on the key-state
    field name.
17. The Jest preset's animation timers print an `act()` warning on every focus
    test.
18. Partially mocking `react-native-kepler` in Jest crashes, so remote handling
    cannot be tested the obvious way.

### How was the onboarding experience?

Mixed, and sharply so. The distance from zero to a running app on the virtual
device is short and well served. The distance from a running app to a *playing
video* is long, undocumented in places, actively contradictory in others, and
almost entirely undiagnosable because of entry 2. Eight of the eighteen entries
would have collapsed into minutes rather than hours if media errors carried a
reason string.

### Would you build with these tools again? **Yes.**

The virtual device and the build pipeline are good, and Vega OS is a reasonable
place to put a media app. The reservations are concentrated in one area, media
playback, and they are overwhelmingly diagnosability problems rather than
capability problems. The platform can do the things I needed. It just would not
tell me why it was not doing them.

---

## Feature requests (optional field; priority as Devpost asks: Critical / Important / Nice-to-have)

1. **[Critical] Put a reason string on media errors.** One change, and it
   collapses eight of my eighteen friction entries. Nothing else on this list
   is close in value.
2. **[Important] Consolidate the playback manifest documentation into one page** and
   retire or redirect the two that disagree with it.
3. **[Important] State plainly that decoded frames are not available to app
   JavaScript.** It is an architectural constraint and it belongs in the
   overview, not in a type definition.
4. **[Important] Do not let `vega project generate` overwrite an existing
   `.gitignore`.** Merge, or refuse and warn.
5. **[Important] Make `AudioPlayer` throw if used before `initialize()`** rather
   than failing silently.
6. **[Nice-to-have] Give `Video` a sane default size** instead of NaN, or throw.
7. **[Important] Document `setMediaControlFocus`** and un-hide it, so apps know
   how to receive voice transport commands.
8. **[Nice-to-have] An SDK-free `build-vega --js-only`** for CI on Linux runners.
9. **[Nice-to-have] Document enum member names in prose**, not only in the types.

---

## Before submitting, the checklist

- [ ] Optional but strong: `export GEMINI_API_KEY=...` and
      `python3 -m aloud.films build` to regenerate every track with a hosted
      model, then compare a few cues against the shipped ones and keep the
      better set. The shipped tracks are already real (Qwen3-VL on CPU).
- [ ] `python3 -m aloud.films fetch`, build, install, and walk
      `docs/MAC_CHECKLIST.md` on the Vega Virtual Device.
- [ ] Video under 3:00 per `docs/DEMO_SCRIPT.md`, public on YouTube, showing
      the Vega Virtual Device, hero inside the first 20 seconds.
- [ ] Blender credits in the video and its description (above).
- [ ] Merge `first-place` into `master` (the default branch still has the
      September README, which says "live"), or point the Devpost link at the
      branch.
- [ ] Repository public with the MIT licence visible, **or** private and shared
      with testing@devpost.com **and all six Amazon reviewers** listed in the
      rules and FAQ: `chris-trag`, `knmeiss`, `giolaq`, `anishamalde`,
      `mosesroth`, `emersonsklar`. Invitations expire after 7 days, so send
      them no earlier than 16 October. Run a secret sweep first.
      ```bash
      for u in chris-trag knmeiss giolaq anishamalde mosesroth emersonsklar; do
        gh api -X PUT repos/ubmids/aloud/collaborators/$u -f permission=pull
      done
      # testing@devpost.com: Settings > Collaborators > Add people, by email
      ```
- [ ] About text and topics: `gh repo edit ubmids/aloud --description "Films
      that describe themselves, on Fire TV (Vega OS)" --add-topic fire-tv
      --add-topic vega-os --add-topic audio-description --add-topic accessibility`
- [ ] The footage question answered by the hackathon team (the FAQ asks
      entrants to check how much Creative Commons footage a video may use
      before finalising it), and the reply kept.
- [ ] Product Feedback and feature requests pasted (above); friction log linked.
- [ ] Submitted before 23 October, 12:00 PDT (19:00 UTC).
