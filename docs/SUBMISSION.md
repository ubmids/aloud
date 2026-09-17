# Submission copy, Aloud — Amazon Developer Hackathon, Fire TV track

Deadline **Friday 23 October 2026, 12:00 PDT**. Devpost: amazonappdev2026.

Four equally weighted criteria at 25% each: Tech Implementation, Design,
Potential Impact, Quality of the Idea. Up to 10% bonus for a friction log,
which `docs/FRICTION_LOG.md` already is, with 13 entries.

**Stage One gate, confirmed met:** the track requires only that the project
runs on Fire OS or Vega OS, any framework. The demo video must show it running
"on an actual Fire TV device or the Fire TV/Vega simulator". The Vega simulator
boots locally with no Amazon developer account, and Aloud installs and runs on
it, verified 17 September. The rules do not require a deployed or published
app, so the account is not on the critical path.

---

## Elevator pitch (200 characters)

Audio description exists for a tiny fraction of content because making it is
manual and expensive. Aloud is a Fire TV app that generates it live and speaks
it into the gaps between dialogue, never over it.

## Text description

Audio description, the narration track that lets blind and low vision people
follow what is happening on screen, exists for a tiny fraction of content,
because producing it is manual and expensive. Meanwhile every streaming app
assumes a viewer who can see it.

Aloud is a Fire TV app for Vega OS that generates audio description live and
speaks it into the gaps between dialogue. A vision model reads frames on a
lookahead buffer, a compression step writes a description sized to fit the
silence actually available, and the speech lands in the window before the next
line of dialogue.

Close your eyes. The television tells you what you are missing, without ever
talking over anyone.

## The hard part, and why it is the whole project

Anyone can caption a frame. The difficulty is scheduling.

You have to find the silence windows, predict how long each one is, and
generate a description that fits without clipping or overrunning into dialogue.
Landing a description on top of a line of dialogue is this product's one
unforgivable failure: it does not degrade the experience, it destroys it, and
it destroys it for the exact viewer who has no other way to follow the film.
That scheduling problem is the difference between this and a captioning toy.

Four decisions follow from taking it seriously.

**Gap detection finds the absence of speech, not the absence of sound.** A loud
musical passage is correctly a place a description can go. A quiet pause
between two halves of a sentence is correctly not.

**Descriptions are fitted by measurement, not estimation.** The pipeline
synthesises the candidate and measures how long it actually takes to say.
Estimating from word count carried 0.62 seconds of error against gaps of a
second and a half, which is the difference between fitting and talking over the
next line.

**The planner describes visual change, not the frame.** A gap with nothing new
behind it gets no cue at all, because a voice restating the same room every few
seconds is worse than silence. On the 52 second demo clip the backend finds
nine gaps and deliberately leaves five of them silent. That is the planner
working, not a shortfall.

**The timed track refuses to be written if any cue would land on dialogue.** The
safety property is enforced at the point of writing rather than checked
afterwards, so a bad track cannot exist to be shipped by accident.

That last one came with a lesson worth putting in the submission rather than
hiding. The track being correct and the *film* being correct are two different
claims, and only one of them was tested. Each description is placed into the
exported mix by a single delay in milliseconds, and nothing checked it, so a
description could play at the wrong moment in the finished film while the track
validated perfectly, because nothing in a timed track describes the mix. The
suite now measures the mixed audio inside each cue's own window. It was found
by mutation testing the pipeline, which turned out to sit at 3% because no test
had ever imported it.

## The player side

Vega OS exposes `currentTime` and a `timeupdate` that fires about four times a
second, and that is all you get. The scheduler built on top of it refuses to
start a description that the rest of the gap can no longer hold, handles
seeking in both directions, and shrinks its window at faster playback rates.

The app plays the bundled trailer through
`@amazon-devices/react-native-w3cmedia` and speaks its descriptions from audio
synthesised in advance and bundled beside the film. Verified on the Vega Virtual
Device: the film runs to its end, every cue fires exactly once, and the film
never pauses underneath them.

## Demo footage and licensing

`tv/assets/sintel-trailer.mp4` is the trailer for **Sintel**, copyright Blender
Foundation, durian.blender.org, released under CC BY 3.0, re-encoded to 640x360
to bring it from 7.6MB to 1.9MB because it is bundled into the app package.

It was chosen over Big Buck Bunny, the more obvious Blender film, for one
reason: Sintel has dialogue and Big Buck Bunny has none. A film with no speech
in it is all gap, so it would demonstrate nothing about the only hard problem
here.

---

## Product Feedback (REQUIRED FIELD)

> Every claim below is drawn from `docs/FRICTION_LOG.md`, which has full
> reproduction steps, severity and a suggested fix for each of its 13 entries.

### Which developer tools, APIs and SDKs did you use, and for what?

- **Vega SDK 0.24.9914** and the `vega` CLI, for build, virtual device and app
  install.
- **`@amazon-devices/react-native-kepler` 4.0** and **React Native 0.83** for
  the app.
- **`@amazon-devices/react-native-w3cmedia` 2.3** for video playback, and its
  `AudioPlayer` for speaking the description cues.
- **Vega Virtual Device** for verification, since it is what the rules accept
  in place of hardware.
- Python 3.14 for the backend pipeline: gap detection, fitting, planning,
  track writing and mixing. 128 tests, mutation tested with a sibling tool from
  the same sprint.

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

Thirteen entries, two of them critical. In rough order of cost:

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

### How was the onboarding experience?

Mixed, and sharply so. The distance from zero to a running app on the virtual
device is short and well served. The distance from a running app to a *playing
video* is long, undocumented in places, actively contradictory in others, and
almost entirely undiagnosable because of entry 2. Eight of the thirteen entries
would have collapsed into minutes rather than hours if media errors carried a
reason string.

### Would you build with these tools again? **Yes.**

The virtual device and the build pipeline are good, and Vega OS is a reasonable
place to put a media app. The reservations are concentrated in one area, media
playback, and they are overwhelmingly diagnosability problems rather than
capability problems. The platform can do the things I needed. It just would not
tell me why it was not doing them.

---

## Feature requests (optional field, priority in brackets)

1. **[Critical] Put a reason string on media errors.** One change, and it
   collapses eight of my thirteen friction entries. Nothing else on this list
   is close in value.
2. **[High] Consolidate the playback manifest documentation into one page** and
   retire or redirect the two that disagree with it.
3. **[High] State plainly that decoded frames are not available to app
   JavaScript.** It is an architectural constraint and it belongs in the
   overview, not in a type definition.
4. **[High] Do not let `vega project generate` overwrite an existing
   `.gitignore`.** Merge, or refuse and warn.
5. **[Medium] Make `AudioPlayer` throw if used before `initialize()`** rather
   than failing silently.
6. **[Medium] Give `Video` a sane default size** instead of NaN, or throw.
7. **[Low] Document enum member names in prose**, not only in the types.

---

## Demo video script

Under 3 minutes, YouTube or Vimeo, public. Must show the project running on a
Fire TV device or the Vega simulator. Screen capture the Vega Virtual Device
window.

> **Do this first.** Regenerate the track with a real vision endpoint before
> filming. The bundled `tv/src/data/description.json` currently reads "The
> scene changes to a new shot in the film" because no vision endpoint was
> configured when it was generated. That is the stub describer being honest,
> and it is the right default, but it is a flat demo. With
> `ALOUD_LLM_BASE_URL`, `ALOUD_LLM_API_KEY` and `ALOUD_LLM_MODEL` set, rerun
> `python3 -m aloud tv/assets/sintel-trailer.mp4 --out out/`, copy the track
> back into `tv/src/data/`, rebuild and reinstall. This single step is the
> largest available improvement to this submission.

**0:00 to 0:15, close your eyes.** On screen: the trailer playing, picture
visible. Then the picture goes black while the audio continues. Say nothing for
five seconds. Let the judge experience a film they cannot follow.

**0:15 to 0:35, the problem.** Say: "Audio description is the narration track
that lets blind and low vision people follow what is on screen. It exists for a
tiny fraction of content, because making it is manual and expensive. Every
streaming app assumes a viewer who can see it."

**0:35 to 1:10, the same clip, described.** Play it again on the Vega device
with Aloud running. The descriptions land in the gaps. Say: "Same clip. The
television is describing itself, live, on a Fire TV."

**1:10 to 1:50, the hard part.** On screen: the gap timeline, nine gaps, four
used and five deliberately left silent. Say: "Anyone can caption a frame. The
difficulty is scheduling. You have to find the silence, predict how long it is,
and write something that fits. Landing on top of dialogue is the one
unforgivable failure, so the track refuses to be written at all if any cue
would." Then: "Five of these nine gaps get no description, because nothing
visible had changed. A voice restating the same room every few seconds is worse
than silence."

**1:50 to 2:15, measurement not estimation.** Say: "Descriptions are fitted by
synthesising them and measuring them, not by counting words. Estimating carried
0.62 seconds of error against gaps of a second and a half, which is exactly the
difference between fitting and talking over the next line."

**2:15 to 2:40, the player.** Say: "Vega gives you `currentTime` and a
`timeupdate` that fires four times a second. That is all. So the scheduler
refuses to start a description the rest of the gap can no longer hold, handles
seeking in both directions, and shrinks its window when you speed the film up."
Show a seek, and a rate change.

**2:40 to 2:55, close.** Back to the black screen with description playing.
Say: "Close your eyes. The television tells you what you are missing, without
ever talking over anyone."

### Shot list

1. Trailer playing with picture, then picture black, audio only, five seconds.
2. The same clip on the Vega device with Aloud running and describing.
3. The gap timeline, nine gaps, five deliberately silent.
4. A cue being synthesised and measured.
5. A seek backwards and forwards, and a playback rate change.
6. Black screen, description playing, close.

---

## Before submitting, the checklist

- [ ] **Regenerate the description track with a real vision endpoint**, then
      rebuild and reinstall. Biggest single improvement available.
- [ ] Demo video under 3 minutes, on YouTube or Vimeo, publicly visible,
      showing it running on the Vega simulator
- [ ] Sintel attribution visible in the video or its description, CC BY 3.0
- [ ] Repository public with licence visible in About, or shared with
      testing@devpost.com
- [ ] Product Feedback field filled in, above
- [ ] Friction log attached, `docs/FRICTION_LOG.md`, 13 entries, for the bonus
- [ ] Feature requests submitted with priorities
- [ ] Run the device `--no-gui` for any scripted verification, it seizes the
      Mac's audio device otherwise, and clear orphaned crashpad handlers after
- [ ] Secret sweep before flipping the repo public
- [ ] Submitted before 23 October, 12:00 PDT
