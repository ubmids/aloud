# Engineering notebook

This is the build record behind aloud: what was measured, what broke, and what
each fix cost. The product description is in the [README](../README.md); the
detector and describer work from the first-place branch is in
[EVALUATION.md](EVALUATION.md) and [DESCRIBERS.md](DESCRIBERS.md).

Two corrections to the history below, so nothing here contradicts the product.
The descriptions are written **ahead of time**, per title, and shipped as a timed
track; nothing is generated while the film plays. And the Vega app is built: it
was verified on the Vega Virtual Device on 17 September, and the remote-driven
catalogue was added on the first-place branch (see MAC_CHECKLIST.md for what is
still to be checked on the Vega Virtual Device).

## The hard part
Gap detection and budget-constrained description. You have to find the silence windows,
predict how long they are, and generate a description that fits without clipping or
overrunning into dialogue. That scheduling problem is the difference between this and a
captioning toy.

## Demo footage

`tv/assets/sintel-trailer.mp4` is the trailer for **Sintel**, (c) copyright
Blender Foundation, [durian.blender.org](https://durian.blender.org), released
under the [Creative Commons Attribution 3.0
licence](https://creativecommons.org/licenses/by/3.0/). It is downloaded from
[download.blender.org/durian/trailer/sintel_trailer-720p.mp4](https://download.blender.org/durian/trailer/sintel_trailer-720p.mp4)
and re-encoded to 640x360 to bring it from 7.6MB to 1.9MB, because it is bundled
into the app package and into this repository.

It was chosen over Big Buck Bunny, the more obvious Blender film, for one
reason: Sintel has dialogue and Big Buck Bunny has none. A film with no speech in
it is all gap, so it would demonstrate nothing about the only hard problem here,
which is placing a description in the silence *between lines* without landing on
the next one. The trailer is 52 seconds and the backend finds nine gaps in it.

## Run it

```bash
pip install -r requirements.txt
python3 -m aloud film.mp4 --out out/
```

Writes `out/description.vtt`, `out/description.json`, and `out/described.mp4`,
which is the film with the descriptions mixed into its own audio. Play that one
with your eyes shut.

It runs with no key. Without a vision endpoint configured it uses a stub
describer that is obviously not looking at the picture, deliberately, so a
missing key can never be mistaken for a working system. Set
`ALOUD_LLM_BASE_URL`, `ALOUD_LLM_API_KEY` and `ALOUD_LLM_MODEL` for the real one.

```bash
python3 tests/test_logic.py         # the fast one, about a second, no subprocesses
python3 tests/test_real_audio.py    # run this one next, it uses real voices
python3 tests/test_pipeline.py
python3 tests/test_planning.py
python3 tests/test_caption.py
python3 tests/test_film.py          # the whole pipeline, on a film it builds
cd tv && node test/schedule.test.mjs
```

## What is built

- **Gap detection** that finds the absence of *speech* rather than the absence
  of sound, so a loud musical passage is correctly a place a description can go.
- **Description fitting by measurement.** The pipeline synthesises the candidate
  and measures it rather than estimating, because estimating carried 0.62s of
  error against gaps of a second and a half.
- **Scene planning** that describes visual *change*. A gap with nothing new
  behind it gets no cue, because a voice restating the same room every few
  seconds is worse than silence.
- **A timed track** in WebVTT and JSON that refuses to be written if any cue
  would land on dialogue.
- **A mix** with a per-cue duck measured from the film underneath it.
- **A player-side scheduler** for Vega OS, which only exposes `currentTime` and
  a `timeupdate` that fires about four times a second. It refuses to start a
  description that the rest of the gap can no longer hold, handles seeking in
  both directions, and shrinks the window at faster playback rates.

## The Fire TV app

```bash
cd tv
export PATH="$HOME/vega/bin:$PATH"
npm install --fetch-timeout=1800000 --fetch-retries=5
npm run build
vega virtual-device start
vega run-app build/aarch64-release/aloud_aarch64.vpkg
```

It plays the bundled trailer through `@amazon-devices/react-native-w3cmedia` and
speaks the four descriptions in `tv/src/data/description.json`, each from audio
synthesised in advance and bundled beside the film. Verified on the Vega Virtual
Device: the film runs to its end, all four cues fire exactly once, and the film
never pauses underneath them.

The track in `tv/src/data/description.json` is the real output of the backend run
on this exact clip, and the descriptions in it read *"The scene changes to a new
shot in the film"* because no vision endpoint was configured when it was
generated. That is the stub describer being honest rather than a model writing
badly, and it is left as generated. The timing around it is real: real gaps, real
measured speech durations, real placement.

Five of the nine gaps are left silent, because nothing visible had changed since
the previous description. That is the planner working, not a shortfall.

### What the screen shows

Audio description is invisible. A still of this app playing a film is a still of
the film, so the screen shows what the ear is getting. The picture sits beside a
panel carrying the sentence currently being spoken, which arrives at full
brightness and settles back once the voice stops. Underneath both of them is the
schedule, drawn at two scales.

The strip is the whole film: dialogue as a solid bar, the silences cut out of it
as recesses, and each description sitting inside one with the gap still visible
around it. Below the strip, the silence the playhead is in is blown up to the
full width, because that is where the margin becomes legible. This much quiet,
this much speech, this much still clear when the voice stops. At film scale that
margin is four pixels. At gap scale it is the product.

A sighted viewer can therefore check the claim the whole system rests on without
being asked to trust it. Watch the playhead cross a lit block and a description
starts. Watch it cross the space between blocks and the film talks instead.

The interface also practises what the app is about. Nothing is told by colour
alone, every tone that carries words clears 4.5:1 against what it sits on, focus
moves rather than recolours, the settings are named in a viewer's language
rather than the pipeline's, and the panel showing the spoken sentence is
deliberately not an accessibility live region: a screen reader user is already
hearing that sentence in the app's own voice, and announcing it a second time
would talk over the film at the one moment this system exists to keep quiet.

## Architecture, and the spike that set it

Vega OS does **not** expose decoded video frames to app JavaScript. Playback is
W3C Media over GStreamer with hardware decode, and there is no canvas, no
`requestVideoFrameCallback`, no texture access.

So descriptions are generated server-side from the source and delivered as a
timed track, which the app fires against `currentTime`. That is the better
architecture regardless: it is how real audio description already ships, it is
cacheable, a human describer can review it before it goes out, and it splits the
two risks apart so the hard problem could be built and tested with no SDK at all.

## What the numbers cost to learn

`docs/CALIBRATION.md` has the measurements. The short version is that every
constant in this pipeline started as a guess and every guess was wrong, and the
synthetic test fixtures hid it. Real voices score 0.52 to 0.66 on the speech-band
measure where the synthetic fixture scores 0.99, so every early test passed with
half a point of margin that does not exist. Behind that margin sat two faults:
rain scores **higher** than a human voice on speech-band energy alone, and a
music bed misreading 7.4% of its frames destroyed a perfectly good gap.

## What Mutiny found here

Mutiny, a sibling project in the same sprint, breaks the source thousands of
ways and reports which tests never notice. Pointed at this repository it showed
that **56% of breakages went unnoticed**, and the findings were not noise.

The worst was the safety check itself. `validate()` decides whether a cue sits
inside a gap, which is the one rule this system must never break, and both its
boundary and the direction of its tolerance were unprotected. The VTT timestamp
formatting had no test at all, so a track could have shipped with wrong times
and everything would still have been green.

Then it showed that only one of `schedule()`'s three alignments was exercised.
Writing the missing test found a real bug: `align="centre"` returned an end
three seconds past a two second gap when handed a cue too long to fit, which is
the exact overrun this project exists to prevent. It was unreachable in
practice, because the pipeline only asks for cues that already fit. That is
precisely why nothing caught it.

It also found that this suite was not hermetic: the test film was written to a
fixed path in `/tmp`, so parallel runs raced on the same file. Per-process now.

Nine tests later and one bug fixed: **44% to 63%** on the timed-track module.

### Round two: the modules the slow suites could not reach

`budget.py` and `gaps.py` carry the safety property and had never been mutation
tested, for a practical reason. The suites that cover them shell out to a
synthesiser and to ffmpeg and cost about thirty seconds a run, and a mutation
tester runs the suite once per mutant, so a single pass over `budget.py` alone
is hours. The answer was `tests/test_logic.py`: the same logic against a stub
synthesiser with a duration model the tests own and audio made of tones, and
sixty five tests in about a second. The real fixtures stay exactly where they
were, because a synthetic voice scores 0.99 on the speech band where a real one
scores 0.55, and that margin is where two real faults once hid.

It found a second real bug, in the same shape as the first: `fit()`, the
estimate-only path for when no synthesiser is available, reported `fits=True`
for descriptions that overran. Twice over. It never held back the 0.62s of
calibrated estimator error the constant beside it exists for, and it truncated
by word where the measured path had been fixed to cut only at clause
boundaries, so it happily produced "A man in a grey coat crosses the." The
truncation rule now lives in one place and both paths go through it.

The rest were missing tests, and the ones worth naming are the safety ones. The
opening window in the smoother could be widened until it deleted a real line of
dialogue, joining the gaps on either side into one that a description would then
play straight over, and nothing noticed. Neither the 2Hz nor the 8Hz end of the
syllable-rhythm band was pinned, so the measurement that separates a voice from
rain could drift either way. The frame-to-seconds conversion could be off by a
tenth of a percent, which is four milliseconds in a fixture and three and a half
seconds by the end of a feature. Every word in the dangling-word list could be
removed one at a time without a single failure.

Mutation score before and after, where before is the suite as it stood and after
is that suite plus the new one. The slow suites cost 30 to 70 seconds a run, so
budget, gaps and synth are measured on an evenly spaced sample of their mutants
rather than all of them, and the sample size is given:

| module | before | after | mutants |
|---|---|---|---|
| `budget.py` | **17%** | **83%** | 76 of 250, every third |
| `gaps.py` | **72%** | **84%** | 25 of 293, every tenth |
| `caption.py` | **52%** | **89%** | all 88 |
| `synth.py` | **61%** | **72%** | 18 of 48, every other |

Mutiny also reported what it should: on a loaded machine, 13% of the mutants in
the `budget.py` run changed their verdict between runs. That is not a finding
about the tests, it is the suites that shell out to `say` being at the mercy of
a busy speech daemon, and it is the clearest argument for the hermetic half
existing at all. Findings are confirmed before they are published, so none of
those reached the table.

Some survivors are equivalent mutants and are written up as such rather than
chased: `_shorten` ignores the word count it is passed, so every mutation of
that arithmetic is a no-op; `max(1, count)` in the syllable counter makes the
silent-e boundary unreachable; numpy treats `reshape(-2, n)` exactly like
`reshape(-1, n)`; and a `"Fit"` return annotation is never evaluated. The score
is a floor, not a grade.

### Round three: the modules nothing had pointed at

`pipeline.py` is the file that runs the other five in order, and no suite
imported it. Mutiny scored it at **3%**, which is the score an untested module
gets: the order of the stages, what happens when the describer fails partway
through a film, and the whole mix were resting on nothing. `tests/test_film.py`
is the answer, a film built out of colour and tones with a stub describer and a
stub voice, so the end to end path runs with no key, no network and no speech
daemon.

The one that would have been worst in front of a viewer was in the mix rather
than the track. Each cue is placed into the finished film by a delay written in
milliseconds, and that delay had no test, so a description could play at
entirely the wrong moment with the track still validating perfectly. Nothing in
a timed track describes the mix. The only way to know is to listen to the
output, which the suite now does: it measures the mixed audio in the cue's own
window and finds speech there and quiet after it.

`scenes.py` was at **45%** and the gap was the frame. `frame_at` decides what
the describer looks at and had no test of any kind, so a dropped or nudged seek
would have every description in the film written about a shot the viewer is not
on, which is worse than silence because it is confident and wrong and reads as a
perfectly good sentence. The test film is three flat colours precisely so a test
can say which frame came back. Its cuts were also moved off whole seconds,
because the old film cut at 3s and 6s and a shot time rounded to the nearest
second was therefore identical to the right answer.

In `gaps.py` the findings were about what the fixtures never varied.

Every smoothing test hands `_smooth` its two windows explicitly, so `CLOSE_S`
and `OPEN_S`, the values a real film is actually processed with, were never
exercised at all and either could be zeroed with the file still green. They are
the two properties the detector was measured for: the quiet tail of a line stays
part of the line, and one misread frame in a music bed does not split a usable
gap into two unusable ones.

Every fixture was also at full scale, and no film is. The syllable measure
divides one energy sum by another and guards the division against zero, and
moving that guard anywhere off zero reads a normally mixed film as one
continuous silence, which puts a description over every line in it. At full
scale the numbers involved are large enough that the guard never fires. A line
at a fifth and a twentieth of full scale now has to be dialogue too.

The top of the syllable band had the same shape of hole. The tests asked about
4Hz in the middle of it and 9Hz outside it, so the edge itself could move a
whole hertz unnoticed, and at 7Hz anyone speaking quickly stops counting as
speech: the gaps either side of them join and the description plays over the
sentence.

`synth.py` reported a working voice on a machine with `say` and no ffmpeg, or
ffmpeg and no `say`, and the failure would arrive as a subprocess error in the
middle of a film instead of a missing voice before it starts. Its measured
duration, the one number the whole schedule is built on, could also be rounded
to the nearest second with nothing noticing: a 2.4s description handed a 2.0s
window is a voice still going when the next line starts.

`calibrate.py` prints the constants at the top of `budget.py`, and it can only
do that honestly if it fits the same five terms the estimator is made of. The
features are now written down once and the test says so, because a fit against
a different model still converges, still reports a small residual, and hands
over numbers for a model nobody runs. It was also telling the operator to set a
`SECONDS_PER_DIGIT` that `budget.py` does not have, since a digit there is
charged as a syllable. That line now says which constant it means.

| module | before | after | mutants | suite |
|---|---|---|---|---|
| `pipeline.py` | **3%** | **54%** | 151 | `test_film.py`, new |
| `scenes.py` | **45%** | **71%** | 104 | `test_planning.py` |
| `gaps.py` | **73%** | **76%** | 293 | `test_logic.py` |
| `budget.py` | **81%** | **84%** | 248 | `test_logic.py` |
| `synth.py` | **60%** | **67%** | 48, then 54 | logic + pipeline |
| `caption.py` | **88%** | **88%** | 86 | `test_caption.py` |
| `calibrate.py` | **0%** | **8%** | 115 | `test_logic.py` |

Every row is every mutant in the file, not a sample, which is why some of them
sit below the sampled numbers in the table above: the hermetic suite made the
full runs affordable.

Mutiny reported the real-voice suite as **not deterministic**, six mutants in
forty two changing their answer between runs, and that outranks everything else
here. The flips land on mutations that cannot change behaviour, a temp
directory prefix and a filename stem, which is the signature of the suite
failing for its own reasons rather than the mutant's. Two things were wrong. One
fixture built its room tone from an unseeded generator, so the suite could
answer differently on different runs by construction; it is seeded now. And the
suite asked `say` for the same eight sentences fifteen times, because a sentence
is measured, then measured again, then spoken. macOS has one speech daemon for
the whole machine, and a mutation run drives several hundred copies of a suite
through it. Measured lengths are cached per voice now, which halves how hard a
parallel run leans on it, and is worth having anyway: synthesis is the slowest
thing in this pipeline.

Not chased, and why. `caption.py` at 88% has ten survivors and all of them are a
timeout constant, an error message, a temperature or a default model name;
`rstrip("/")` survives only because httpx normalises the double slash before the
request leaves. A wider closing window in `gaps.py` loses gaps rather than
placing a cue wrongly, and is bounded by the minimum gap length regardless.
Moving either edge of the speech band by one hertz cannot change which FFT bins
are selected. The near-silence guard in `speechiness` is unreachable behind the
absolute floor above it, since any frame quiet enough to trip it has already
been zeroed. The right channel of the mix delay is a no-op because the cue audio
is mono. Dropping the `-v` and `-r` flags gives you the machine's default voice,
which is a wrong voice rather than a wrong schedule, since the schedule is
measured from whatever voice actually spoke. And most of `calibrate.py` is a table of phrases and a print loop for a
human to read, which is why it stays at 8% rather than being dressed up.
