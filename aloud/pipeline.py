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
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

from .budget import fit_generated, words_for
from .gaps import find_gaps, load_audio
from .scenes import detect_shots, frame_at, plan_descriptions
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


def describe_film(video: str, *, captioner=None, synth=None,
                  out_dir: str | None = None, align: str = "start") -> Result:
    from .caption import captioner_from_env

    captioner = captioner or captioner_from_env()
    synth = synth or Synth()
    out_dir = out_dir or tempfile.mkdtemp(prefix="aloud-")
    os.makedirs(out_dir, exist_ok=True)
    frames_dir = os.path.join(out_dir, "frames")
    cues_dir = os.path.join(out_dir, "cues")

    audio, sr = load_audio(video)
    gaps = find_gaps(audio, sr)
    shots = detect_shots(video)
    plans = plan_descriptions(gaps, shots)

    track, skipped = Track(source=video), []
    for plan in plans:
        if not plan.worth_describing:
            skipped.append((plan.gap, plan.reason))
            continue

        frame = frame_at(video, plan.describe_at,
                         os.path.join(frames_dir, f"{plan.describe_at:.3f}.jpg"))

        # One bad frame must not cost the whole film. A describer that raises
        # here is a real possibility (a rate limit, a refused image, a timeout)
        # and the right answer is to leave that gap silent and carry on, which
        # is exactly what a gap with nothing worth saying already gets.
        try:
            fitted = fit_generated(lambda n: captioner(frame, n),
                                   plan.gap.duration, synth)
        except Exception as e:
            skipped.append((plan.gap, f"the describer failed: {type(e).__name__}"))
            continue

        if not fitted.fits or not fitted.text:
            skipped.append((plan.gap, "nothing useful fitted in the time"))
            continue

        spoken = synth.speak(fitted.text, out_dir=cues_dir)
        start, end = schedule(plan.gap, spoken.seconds, align=align)
        track.cues.append(Cue(round(start, 3), round(end, 3), fitted.text,
                              audio=spoken.path,
                              gap=(plan.gap.start, plan.gap.end)))

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
