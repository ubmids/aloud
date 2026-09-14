"""Finding the holes in the dialogue that a description can live in.

The naive version of this thresholds raw loudness and calls the quiet parts
silence. That fails immediately on real film, where the quiet parts are full of
score, room tone, rain and footsteps. A description dropped into a swell of
music is not in a gap, it is on top of the film.

What we actually need is the absence of *speech*, which is a different question
from the absence of *sound*. Speech has most of its energy between roughly 300Hz
and 3400Hz, the band telephones were designed around. So the measure here is the
proportion of a frame's energy that falls in the speech band, not the frame's
loudness: a loud orchestral passage has plenty of energy and little of it in a
speech-shaped distribution, and reads correctly as a gap.

Everything is deliberately explainable. A black-box voice activity detector
would score better on paper and leave nothing to reason about when it puts a
description over a line of dialogue.
"""
import shutil
import subprocess
import wave
from dataclasses import dataclass

import numpy as np

# The telephone band is 300-3400Hz, but a detector that starts at 300 throws
# away the fundamental of most male voices (85-255Hz) and scores them as
# non-speech. Starting at 200 keeps enough of it to matter without letting in
# the low rumble that scores and room tone live in.
SPEECH_LOW, SPEECH_HIGH = 200.0, 3500.0

# Absolute, because a relative one is not safe. This gate was originally a
# percentile of the track's own loudness, which meant whether a line of dialogue
# registered as speech depended on how much quiet material happened to sit
# elsewhere in the file. A fixture containing a silent passage passed; the same
# code on a track without one reported the entire film as a gap. Audio is
# normalised to plus or minus one, so an absolute floor is meaningful and cannot
# be moved by unrelated content.
BAND_RMS_FLOOR = 0.005
FRAME_MS = 20.0
# Below this a gap cannot carry anything, so detecting it only wastes the rest
# of the pipeline's time. The number is measured, not chosen: the longest of the
# shortest useful descriptions ("Nothing moves.", "A man crosses.") runs to about
# 1.15s on the reference voice, and with the 15% headroom the schedule leaves at
# each end that needs a gap of roughly 1.35s. A guessed 0.9s let through gaps
# that every describer then failed to fill.
MIN_GAP_S = 1.35


@dataclass
class Gap:
    start: float
    end: float

    @property
    def duration(self) -> float:
        return self.end - self.start

    def __repr__(self):
        return f"Gap({self.start:.2f}-{self.end:.2f}s, {self.duration:.2f}s)"


def load_audio(path: str, sr: int = 16000) -> tuple[np.ndarray, int]:
    """Mono float32 at `sr`. Uses ffmpeg for anything that is not already a
    plain PCM wav, so the pipeline accepts whatever the film arrives as."""
    if path.lower().endswith(".wav"):
        try:
            with wave.open(path, "rb") as w:
                if w.getnchannels() == 1 and w.getframerate() == sr \
                        and w.getsampwidth() == 2:
                    raw = w.readframes(w.getnframes())
                    return np.frombuffer(raw, "<i2").astype(np.float32) / 32768.0, sr
        except wave.Error:
            pass
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to read this file")
    out = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(sr),
         "-f", "s16le", "-"], capture_output=True, check=True).stdout
    return np.frombuffer(out, "<i2").astype(np.float32) / 32768.0, sr


def speechiness(audio: np.ndarray, sr: int, frame_ms: float = FRAME_MS) -> np.ndarray:
    """Per-frame fraction of energy sitting in the speech band.

    Returns values in 0..1, one per frame. Silence returns 0 rather than a
    meaningless ratio of two near-zero numbers.
    """
    n = max(1, int(sr * frame_ms / 1000.0))
    usable = (len(audio) // n) * n
    if usable == 0:
        return np.zeros(0, dtype=np.float32)
    frames = audio[:usable].reshape(-1, n)
    window = np.hanning(n).astype(np.float32)
    spec = np.abs(np.fft.rfft(frames * window, axis=1)) ** 2
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    band = (freqs >= SPEECH_LOW) & (freqs <= SPEECH_HIGH)

    total = spec.sum(axis=1)
    in_band = spec[:, band].sum(axis=1)
    # A frame with no energy at all is silence, not "0% speech-shaped noise".
    # Guarding here rather than with a global epsilon keeps the ratio honest for
    # frames that do have energy.
    quiet = total < 1e-9
    ratio = np.zeros_like(total)
    ratio[~quiet] = in_band[~quiet] / total[~quiet]

    # Loudness still matters: a near-silent frame whose scraps of energy happen
    # to be speech-shaped is not someone talking. Measured inside the band and
    # against an absolute floor, so the decision for one frame never depends on
    # what the rest of the file contains.
    band_rms = np.sqrt(in_band / n) / np.sqrt(n)
    audible = band_rms > BAND_RMS_FLOOR
    return (ratio * audible).astype(np.float32)


def find_gaps(audio: np.ndarray, sr: int, *, threshold: float = 0.45,
              min_gap: float = MIN_GAP_S, frame_ms: float = FRAME_MS,
              pad: float = 0.15) -> list[Gap]:
    """Windows with no speech in them, long enough to be worth using.

    `pad` is trimmed off each end. Dialogue does not stop cleanly on a frame
    boundary, and a description that begins the instant a line ends sounds like
    an interruption even when it technically is not.
    """
    sp = speechiness(audio, sr, frame_ms)
    if len(sp) == 0:
        return []
    speaking = sp >= threshold
    step = frame_ms / 1000.0

    gaps, run_start = [], None
    for i, talking in enumerate(speaking):
        if not talking and run_start is None:
            run_start = i
        elif talking and run_start is not None:
            gaps.append((run_start * step, i * step))
            run_start = None
    if run_start is not None:
        gaps.append((run_start * step, len(speaking) * step))

    out = []
    for start, end in gaps:
        s, e = start + pad, end - pad
        if e - s >= min_gap:
            out.append(Gap(round(s, 3), round(e, 3)))
    return out
