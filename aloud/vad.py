"""A second, independent ear for speech.

The detector in gaps.py is hand-built and explainable, and on the synthetic and
recorded fixtures it never placed a gap on a line. Then it met a real film.
Run over all of *Tears of Steel* and checked against a dialogue map built from
the film's own production stems (see `aloud.evaluate`), 28 of its 92 gaps
overlapped dialogue, 25 seconds in total. The misses had one shape: a line
spoken over a loud score or an action cue, where the syllable rhythm the
detector relies on is buried under the music's own rhythm.

Silero VAD is a small neural voice detector (2MB, MIT licence, runs in about
a second per film-minute on one CPU core) that is trained on exactly that
situation. On its own it is not safe either: it misses quiet and processed
voices the hand-built detector catches. The two fail in different places, so
the pipeline treats a frame as speech if EITHER hears it, and a gap has to be
silent to both. That union is what took the film from 25 seconds of overlap to
under one, and the remaining fraction is closed by the title's own caption file
(see `aloud.captions`).

The model ships in the repository beside this file, so detection does not
depend on a download and gives the same answer on every machine.
"""
import os

import numpy as np

MODEL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models",
                     "silero_vad.onnx")
SR = 16000
WINDOW = 512          # samples per decision at 16kHz, fixed by the model
CONTEXT = 64          # samples of the previous window the model expects

_SESSION = None


def available() -> bool:
    if os.getenv("ALOUD_NO_VAD"):
        return False
    if not os.path.exists(MODEL):
        return False
    try:
        import onnxruntime  # noqa: F401
    except ImportError:
        return False
    return True


def _session():
    global _SESSION
    if _SESSION is None:
        import onnxruntime as ort
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        _SESSION = ort.InferenceSession(MODEL, opts,
                                        providers=["CPUExecutionProvider"])
    return _SESSION


def probabilities(audio: np.ndarray, sr: int = SR) -> np.ndarray:
    """Speech probability for every 32ms window of 16kHz mono audio."""
    if sr != SR:
        raise ValueError("the voice detector runs at 16kHz")
    sess = _session()
    state = np.zeros((2, 1, 128), np.float32)
    context = np.zeros(CONTEXT, np.float32)
    rate = np.array(SR, dtype=np.int64)
    out = []
    audio = np.asarray(audio, dtype=np.float32)
    for i in range(0, len(audio) - WINDOW + 1, WINDOW):
        chunk = audio[i:i + WINDOW]
        x = np.concatenate([context, chunk])[None, :]
        p, state = sess.run(None, {"input": x, "state": state, "sr": rate})
        context = chunk[-CONTEXT:]
        out.append(float(p[0, 0]))
    return np.array(out, dtype=np.float32)


def speech_frames(audio: np.ndarray, sr: int, frame_ms: float,
                  count: int, threshold: float = 0.3) -> np.ndarray:
    """The detector's opinion, resampled onto the caller's frame grid.

    A frame counts as speech if any 32ms window overlapping it does, so the
    resampling can only widen what the model heard, never narrow it.
    """
    probs = probabilities(audio, sr)
    mask = np.zeros(count, dtype=bool)
    if len(probs) == 0:
        return mask
    win_s = WINDOW / SR
    step = frame_ms / 1000.0
    for j in np.flatnonzero(probs >= threshold):
        a = int((j * win_s) / step)
        b = int(np.ceil(((j + 1) * win_s) / step))
        mask[max(0, a):min(count, b)] = True
    return mask
