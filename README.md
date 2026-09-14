# Aloud

**A television that describes itself.**

Audio description, the narration track that lets blind and low vision people follow what is
happening on screen, exists for a tiny fraction of content, because producing it is manual
and expensive. Meanwhile every streaming app assumes a viewer who can see it.

Aloud is a Fire TV app for Vega OS that generates audio description live and speaks it into
the gaps between dialogue. A vision model reads frames on a lookahead buffer, a compression
step writes a description sized to fit the silence actually available, and speech lands in
the window before the next line of dialogue.

Close your eyes. The television tells you what you are missing, without ever talking over
anyone.

## The hard part
Gap detection and budget-constrained description. You have to find the silence windows,
predict how long they are, and generate a description that fits without clipping or
overrunning into dialogue. That scheduling problem is the difference between this and a
captioning toy.

## Demo footage
Blender open movies (Sintel, Tears of Steel) so everything shown is freely licensed.

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
python3 tests/test_real_audio.py    # run this one first, it uses real voices
python3 tests/test_pipeline.py
python3 tests/test_planning.py
python3 tests/test_caption.py
node app/test/schedule.test.mjs
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

## Status

The whole backend is built and tested. 27 tests in Python, 12 in JavaScript.

Still to do: the Vega app shell around the scheduler, which needs 20GB of disk
for the SDK, and a real vision endpoint for the describer.

## Built for
Build, Ship, Shape: Amazon Developer Hackathon 2026, Fire TV track. Deadline 23 Oct 2026.

## Licence
MIT
