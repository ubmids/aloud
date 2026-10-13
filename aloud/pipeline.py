"""End to end: a film in, a description track out, and audio you can listen to.

The order matters and is not arbitrary.

  1. Find the gaps first. They are the hard constraint, and everything the
     describer writes has to live inside one. Generating descriptions first and
     then hunting for somewhere to put them is how you end up talking over
     dialogue.
  2. Plan what is worth describing. A gap with no visual change behind it gets
     nothing, because a voice restating the same room every few seconds is worse
     than silence.
  3. Only then describe, with the word budget already decided by the gap.
  4. Synthesise and measure. The schedule is built on real durations, never
     estimates.
  5. Validate before writing anything. A track that would land on dialogue is
     refused, not warned about.
"""
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

from .budget import fit_generated, words_for
from .gaps import find_gaps, load_audio
from .scenes import (detect_shots, first_lit_frame, frame_at, next_cut_after,
                     plan_descriptions, split_long_gaps)
from .synth import Synth
from .track import Cue, Track, schedule


@dataclass
class Result:
    track: Track
    gaps: list
    shots: list
    skipped: list          # (gap, why nothing was said)
    audio_path: str | None = None
    ducks: list = None     # (cue start, the gain the film was ducked to)


def stub_captioner(frame_path: str, target_words: int) -> str:
    """A describer that has not seen the frame.

    It exists so the pipeline runs end to end with no key and no network, which
    keeps every other stage testable. It is deliberately obvious about what it
    is: nothing here pretends to have looked at the picture, because a stub that
    invents plausible descriptions would make a broken captioner look like a
    working one.
    """
    n = max(2, target_words)
    base = ["The", "scene", "changes", "to", "a", "new", "shot", "in", "the",
            "film", "as", "the", "story", "moves", "on", "again"]
    return " ".join(base[:n]).rstrip(",") + "."


def _takes(captioner, name: str) -> bool:
    """Whether a describer accepts an optional keyword. Plain functions written
    for the two-argument contract keep working untouched."""
    if getattr(captioner, "takes_context", False):
        return True
    try:
        return name in inspect.signature(captioner).parameters
    except (TypeError, ValueError):
        return False


class _Remembered:
    """Descriptions already written, on disk beside the track.

    A film is a few hundred requests to a describer, and on a CPU that is half
    an hour. A crash, a rate limit or a tweak to the mixer should not cost all
    of it again, so every answer is kept, keyed by everything that could change
    it: which model, which frame, how many words, and what had been said
    before. Change any of those and it is asked afresh.
    """

    def __init__(self, path: str | None):
        self.path = path
        self.answers = {}
        if path and os.path.exists(path):
            try:
                with open(path) as f:
                    self.answers = json.load(f)
            except (OSError, ValueError):
                self.answers = {}

    @staticmethod
    def key(*parts) -> str:
        return hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:24]

    def get(self, key):
        return self.answers.get(key)

    def put(self, key, text):
        self.answers[key] = text
        if self.path:
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(self.answers, f, indent=0)
            os.replace(tmp, self.path)


def _log(quiet: bool, msg: str):
    if not quiet:
        print(msg, file=sys.stderr, flush=True)


def describe_film(video: str, *, captioner=None, synth=None,
                  out_dir: str | None = None, align: str = "start",
                  captions: str | None = None, split: bool = True,
                  memory: int = 3, quiet: bool = True,
                  max_failures: int = 5) -> Result:
    """Describe `video` and return the track.

    `captions` is the title's own SRT or WebVTT file, if it has one. Every cue
    in it is treated as speech whatever the audio says (see captions.py).
    `memory` is how many earlier descriptions the describer is shown, so it
    says what is new instead of reintroducing the same man every cue.
    """
    from .caption import brief_version, captioner_from_env, vacuous

    captioner = captioner or captioner_from_env()
    synth = synth or Synth()
    out_dir = out_dir or tempfile.mkdtemp(prefix="aloud-")
    os.makedirs(out_dir, exist_ok=True)
    frames_dir = os.path.join(out_dir, "frames")
    cues_dir = os.path.join(out_dir, "cues")
    label = getattr(captioner, "label", getattr(captioner, "__name__", "describer"))
    remembered = _Remembered(os.path.join(out_dir, "described.cache.json")
                             if label != "stub_captioner" else None)
    is_stub = captioner is stub_captioner
    with_context = _takes(captioner, "context")
    with_frames = _takes(captioner, "frames")

    also = None
    if captions:
        from .captions import speech_spans
        also = speech_spans(captions)
    audio, sr = load_audio(video)
    gaps = find_gaps(audio, sr, also_speech=also)
    _log(quiet, f"{len(gaps)} gaps in the dialogue")
    shots = detect_shots(video)
    _log(quiet, f"{len(shots)} shot changes")
    windows = split_long_gaps(gaps, shots) if split else gaps
    plans = plan_descriptions(windows, shots)

    track, skipped, said = Track(source=video), [], []
    failures = 0
    for i, plan in enumerate(plans, 1):
        if not plan.worth_describing:
            skipped.append((plan.gap, plan.reason))
            continue

        # Black is not a picture. Look further into the gap for the moment the
        # image comes up, and if it never does within the first half, say
        # nothing: there is not enough of the gap left to describe it well.
        lit = first_lit_frame(video, plan.describe_at,
                              plan.describe_at + max(0.5, plan.gap.duration / 2),
                              frames_dir)
        if lit is None:
            skipped.append((plan.gap, "the screen is dark"))
            continue
        lit_at, frame = lit
        if lit_at > plan.describe_at:
            plan.gap = type(plan.gap)(round(max(plan.gap.start, lit_at - 0.25), 3),
                                      plan.gap.end)
            plan.describe_at = round(lit_at, 3)
            if plan.gap.duration < 1.35:
                skipped.append((plan.gap, "the picture came up too late"))
                continue
        # A second look a second later, if the shot lasts that long, so the
        # describer can see what is moving rather than guess from one still.
        extra = []
        later = plan.describe_at + 1.0
        cut = next_cut_after(shots, plan.describe_at)
        if with_frames and later < plan.gap.end and (cut is None or later < cut - 0.1):
            extra = [frame_at(video, later,
                              os.path.join(frames_dir, f"{later:.3f}.jpg"))]
        context = "\n".join(said[-memory:]) if (with_context and memory) else None

        def describe(n, frame=frame, extra=extra, context=context,
                     at=plan.describe_at):
            key = _Remembered.key(label, brief_version(), round(at, 3), n,
                                  len(extra), context)
            got = remembered.get(key)
            if got is None:
                kw = {}
                if extra:
                    kw["frames"] = extra
                if context:
                    kw["context"] = context
                got = captioner(frame, n, **kw)
                remembered.put(key, got)
            # A sentence about the film instead of what is in it ("Text appears
            # on screen.") is treated as nothing written, so the gap is left
            # silent rather than spent on it.
            # The stub is exempt: it is obvious on purpose, so the plumbing
            # around it can be tested end to end with no model at all.
            return "" if (vacuous(got) and not is_stub) else got

        # One bad frame must not cost the whole film. A describer that raises
        # here is a real possibility (a rate limit, a refused image, a timeout)
        # and the right answer is to leave that gap silent and carry on, which
        # is exactly what a gap with nothing worth saying already gets.
        try:
            fitted = fit_generated(describe, plan.gap.duration, synth)
            failures = 0
        except Exception as e:
            skipped.append((plan.gap, f"the describer failed: {type(e).__name__}"))
            failures += 1
            # One failure is a bad frame. A run of them is a describer that
            # has gone away, and carrying on would write a track that is
            # silent from here to the end and call it finished. That happened:
            # a local model server died a few minutes into a film and the run
            # "completed" with 45 gaps skipped.
            if failures >= max_failures:
                raise RuntimeError(
                    f"the describer failed {failures} times in a row, last "
                    f"with {type(e).__name__}: {e}. Nothing was written; "
                    "answers so far are kept, so rerunning resumes.") from e
            continue

        if not fitted.fits or not fitted.text:
            skipped.append((plan.gap, "nothing useful fitted in the time"))
            continue

        spoken = synth.speak(fitted.text, out_dir=cues_dir)
        start, end = schedule(plan.gap, spoken.seconds, align=align)
        track.cues.append(Cue(round(start, 3), round(end, 3), fitted.text,
                              audio=spoken.path,
                              gap=(plan.gap.start, plan.gap.end)))
        said.append(fitted.text)
        _log(quiet, f"[{i}/{len(plans)}] {start:7.2f}s  {fitted.text}")

    track.describer = label
    track.voice = getattr(synth, "name", type(synth).__name__)
    problems = track.validate(gaps)
    if problems:
        raise ValueError("the pipeline produced an unsafe track:\n  "
                         + "\n  ".join(problems))
    return Result(track, gaps, shots, skipped)


def _rms(audio, sr, start: float, end: float) -> float:
    import numpy as np
    seg = audio[int(max(0.0, start) * sr):int(max(0.0, end) * sr)]
    return float(np.sqrt((seg ** 2).mean())) if len(seg) else 0.0


def mix(video: str, result: Result, out_path: str, *, headroom_db: float = 10.0,
        max_duck_db: float = -24.0) -> str:
    """Lay the descriptions over the film's own audio, ducked per cue.

    This is the artefact that makes the case without any explanation: play it,
    close your eyes, and the television tells you what you are missing.

    The duck is measured, not fixed. A single ducking level was the first
    version and it failed exactly where it mattered: a flat -7dB is plenty under
    room tone and does nothing under a score, so the description over the music
    came out quieter than the music and was simply inaudible. Verifying the
    mixed audio rather than trusting it is what caught that.

    Now each cue gets its own duck, computed from the real level of the film
    underneath it and the real level of the spoken cue, so the description
    always sits `headroom_db` above the bed. Loud passages duck hard, quiet ones
    barely move, and the room never drops out entirely.
    """
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to mix")
    cues = [c for c in result.track.cues if c.audio]
    if not cues:
        raise ValueError("no cues with audio to mix")

    from .gaps import load_audio
    bed_audio, sr = load_audio(video)
    target_ratio = 10 ** (-headroom_db / 20.0)   # bed must sit this far below
    floor = 10 ** (max_duck_db / 20.0)           # never silence the film entirely

    inputs, filters, labels = ["-i", video], [], []
    chain, ducks = "[0:a]", []
    for i, c in enumerate(cues, start=1):
        cue_audio, csr = load_audio(c.audio)
        cue_level = _rms(cue_audio, csr, 0, c.duration)
        bed_level = _rms(bed_audio, sr, c.start, c.end)
        gain = 1.0 if bed_level <= 1e-6 else min(
            1.0, max(floor, (cue_level * target_ratio) / bed_level))
        ducks.append((c, gain))
        chain += (f"volume=enable='between(t,{c.start:.3f},{c.end:.3f})'"
                  f":volume={gain:.4f},")
    filters.append(chain.rstrip(",") + "[bed]")

    for i, (c, _) in enumerate(ducks, start=1):
        inputs += ["-i", c.audio]
        filters.append(f"[{i}:a]adelay={int(c.start * 1000)}|{int(c.start * 1000)}[d{i}]")
        labels.append(f"[d{i}]")

    filters.append(f"[bed]{''.join(labels)}amix=inputs={len(cues) + 1}:"
                   f"normalize=0:duration=first[out]")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *inputs,
         "-filter_complex", ";".join(filters),
         "-map", "0:v?", "-map", "[out]", "-c:v", "copy", out_path],
        check=True, capture_output=True)
    result.audio_path = out_path
    result.ducks = [(c.start, round(g, 4)) for c, g in ducks]
    return out_path
