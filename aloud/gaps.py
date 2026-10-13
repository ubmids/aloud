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

# Syllable rate. A talking person opens and closes their mouth a few times a
# second, which puts a strong peak in the amplitude envelope between roughly 2Hz
# and 8Hz. This is the feature that the speech band alone cannot provide, and
# without it the detector is broken in a way that only real audio reveals:
# broadband sound spreads energy across the speech band and scores *higher* than
# a human voice. Measured on real material, rain scores 0.75 on band energy
# against 0.56 for the quietest real voice, so a band-only detector hears
# dialogue through an entire rainy scene and never emits a single description.
#
# On the syllable rhythm the two separate cleanly:
#   rain 0.23, applause 0.27, orchestral 0.40 against voices at 0.61 to 0.78.
MOD_LOW, MOD_HIGH = 2.0, 8.0
MOD_WINDOW_S = 1.0

# The per-frame decision is noisy, and a scattering of false positives destroys
# gaps rather than shrinking them: a run of non-speech broken every half second
# becomes several runs too short to use, and a perfectly good three second gap
# vanishes. Measured on a realistic track, a music bed misread only 7.4% of its
# frames as speech and lost the entire gap that way.
#
# Nobody speaks for 40 milliseconds and stops. Smoothing the decision over a
# window longer than any single frame but shorter than any real utterance
# removes the scatter without touching genuine speech.
# Two morphological steps, in this order, and the order is the whole point.
#
# CLOSE first: join speech runs separated by less than this. The quiet tail of a
# line fragments into short runs, and dropping them on their own merits ate half
# a second off the end of real dialogue. Closing reattaches the tail to the line
# it belongs to before anything is dropped.
#
# OPEN second: drop what is still a short, isolated run. Nobody speaks for 40
# milliseconds and stops, so whatever survives closing and is still that short
# is detector noise.
#
# Measured over a grid on a track of real voices, rain, an orchestral bed and
# room tone: closing at 0.20s or more gives zero overlap with dialogue at every
# opening value tried. Without closing, the best safe configuration still ate
# 0.12s of a line. The cost is gap time, 6.1s of 10s recovered instead of 9.3s,
# because closing also joins scattered frames inside a music bed. That is the
# right way round. Three seconds less description is a price worth paying for
# never speaking over a line, which is the one thing this system must not do.
CLOSE_S = 0.25
OPEN_S = 0.20

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


def modulation(audio: np.ndarray, sr: int, frame_ms: float = FRAME_MS,
               window_s: float = MOD_WINDOW_S) -> np.ndarray:
    """Per-frame strength of the syllable rhythm, 0..1.

    Measured over a sliding window, because a rhythm is not a property of a
    20ms frame: you need about a second of context to see a mouth opening and
    closing. Frames near the edges reuse the nearest full window rather than
    being scored on a truncated one, since a short window flatters noise.
    """
    n = max(1, int(sr * frame_ms / 1000.0))
    usable = (len(audio) // n) * n
    if usable == 0:
        return np.zeros(0, dtype=np.float32)
    frames = audio[:usable].reshape(-1, n)
    env = np.sqrt((frames ** 2).mean(axis=1))
    count = len(env)

    win = max(8, int(window_s / (frame_ms / 1000.0)))
    if count < win:
        return np.full(count, _mod_index(env), dtype=np.float32)

    out = np.zeros(count, dtype=np.float32)
    half = win // 2
    freqs = np.fft.rfftfreq(win, frame_ms / 1000.0)
    band = (freqs >= MOD_LOW) & (freqs <= MOD_HIGH)
    hann = np.hanning(win)
    for i in range(count):
        start = min(max(0, i - half), count - win)
        seg = env[start:start + win]
        out[i] = _mod_index(seg, band, hann)
    return out


# How much the envelope has to move before its rhythm means anything. The index
# below is a RATIO, the share of the envelope's fluctuation that sits at
# syllable rate, so a steady sound with a one percent ripple can score as highly
# as a voice: a held orchestral chord did exactly that, read as speech, and
# cost a three and a half second gap. A mouth opening and closing moves the
# envelope by well over half its mean; a sustained note moves it by almost
# nothing. Below this depth there are no syllables, whatever their spectrum.
MOD_DEPTH_FLOOR = 0.15


def _mod_index(env: np.ndarray, band=None, hann=None) -> float:
    if len(env) < 8 or env.mean() <= 1e-9:
        return 0.0
    if env.std() / env.mean() < MOD_DEPTH_FLOOR:
        return 0.0
    if band is None:
        freqs = np.fft.rfftfreq(len(env), FRAME_MS / 1000.0)
        band = (freqs >= MOD_LOW) & (freqs <= MOD_HIGH)
    if hann is None:
        hann = np.hanning(len(env))
    spec = np.abs(np.fft.rfft((env - env.mean()) * hann)) ** 2
    total = spec.sum()
    return float(spec[band].sum() / total) if total > 0 else 0.0


def _runs(mask: np.ndarray):
    """[start, end) index pairs for every True run."""
    out, start = [], None
    for i, on in enumerate(mask):
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append((start, i))
            start = None
    if start is not None:
        out.append((start, len(mask)))
    return out


def _smooth(mask: np.ndarray, frame_ms: float, close_s: float,
            open_s: float) -> np.ndarray:
    """Close small holes in speech, then drop what is still too short.

    Two earlier attempts both leaked. A symmetric majority vote shrank real
    lines from both ends. Dropping short runs outright deleted the quiet tail of
    a line, which is genuinely speech and merely hard to detect. Closing before
    opening fixes both, because the tail gets reattached to its line before
    anything is eligible to be dropped.
    """
    step = frame_ms / 1000.0
    out = mask.copy()
    if len(out) == 0:
        return out

    close_frames = max(0, int(close_s / step))
    if close_frames:
        start = None
        for i, on in enumerate(out):
            if not on and start is None:
                start = i
            elif on and start is not None:
                # Only interior holes. A quiet lead-in at the very start of the
                # file is not a hole between two lines.
                if i - start < close_frames and start > 0:
                    out[start:i] = True
                start = None

    open_frames = max(0, int(open_s / step))
    if open_frames:
        for a, b in _runs(out):
            if b - a < open_frames:
                out[a:b] = False
    return out


def find_gaps(audio: np.ndarray, sr: int, *, threshold: float = 0.45,
              mod_threshold: float = 0.50, close_s: float = CLOSE_S,
              open_s: float = OPEN_S,
              min_gap: float = MIN_GAP_S, frame_ms: float = FRAME_MS,
              pad: float = 0.15, vad: bool | None = None,
              also_speech=None) -> list[Gap]:
    """Windows with no speech in them, long enough to be worth using.

    `pad` is trimmed off each end. Dialogue does not stop cleanly on a frame
    boundary, and a description that begins the instant a line ends sounds like
    an interruption even when it technically is not.

    `vad` adds the neural voice detector in vad.py as a second ear: a frame is
    speech if either detector hears it. None means "if it is installed", which
    it is wherever onnxruntime is, because the model ships in the repository.

    `also_speech` is a list of (start, end) seconds that are speech whatever the
    audio says, which is how the title's own caption file is applied. Captions
    are written by people who heard every line, so they catch the dialogue a
    detector misses under a loud score, and they only ever remove gap time.
    """
    sp = speechiness(audio, sr, frame_ms)
    if len(sp) == 0:
        return []
    # BOTH conditions, not either. Speech-shaped energy says the sound could be
    # a voice; the syllable rhythm says something is actually talking. Rain
    # passes the first and fails the second, which is the whole point.
    mod = modulation(audio, sr, frame_ms)
    heard = (sp >= threshold) & (mod >= mod_threshold)
    if vad is None:
        from . import vad as _vad
        vad = _vad.available()
    if vad:
        from . import vad as _vad
        heard = heard | _vad.speech_frames(audio, sr, frame_ms, len(heard))
    speaking = _smooth(heard, frame_ms, close_s, open_s)
    step = frame_ms / 1000.0
    for a, b in (also_speech or ()):
        speaking[max(0, int(a / step)):max(0, int(np.ceil(b / step)))] = True

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
