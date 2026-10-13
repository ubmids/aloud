"""Speech synthesis, and the exact duration of what it produced.

The duration of a spoken sentence is the thing the whole schedule depends on,
and it is cheap to know exactly. Calibrating a syllable model against this voice
left a worst-case error of 0.62 seconds, which against a gap of a second and a
half is the difference between a description and an interruption. So the
pipeline measures rather than predicts, and the estimator in budget.py is
demoted to what it is actually good for: guessing a word target before anything
has been written.

Two voices, one contract. `say` needs no key and no network, so the pipeline
runs end to end on any Mac. Kokoro is an 82M-parameter neural voice that runs on
a CPU in well under real time, so the same pipeline runs on a Linux box with no
GPU and the cues that ship in the app sound like a person rather than a 2005
screen reader. Either way the contract is one method that returns audio and its
true length, and the schedule is built on that length whichever voice spoke.

`ALOUD_TTS=say|kokoro` picks one; otherwise `say` if it exists, then Kokoro if
its model files are where `ALOUD_KOKORO_DIR` (default `~/.cache/aloud/kokoro`)
says they are.
"""
import os
import shutil
import subprocess
import tempfile
import wave
from dataclasses import dataclass


@dataclass
class Spoken:
    text: str
    path: str | None
    seconds: float


KOKORO_MODEL = "kokoro-v1.0.onnx"
KOKORO_VOICES = "voices-v1.0.bin"
KOKORO_DEFAULT_VOICE = "af_heart"

# The tests and older scripts ask for voices by their macOS names. Mapping them
# keeps those suites meaningful on Linux: two different speakers stay two
# different speakers, which is what the real-audio suite is checking.
KOKORO_FOR_SAY = {
    "samantha": "af_heart",
    "daniel": "bm_george",
    "alex": "am_michael",
    "karen": "af_bella",
    "moira": "bf_emma",
}

# `say -r` is words per minute and its default is about 175. Kokoro takes a
# speed multiplier, so the same knob means the same thing on both.
SAY_DEFAULT_WPM = 175.0


def kokoro_dir() -> str:
    return os.path.expanduser(
        os.getenv("ALOUD_KOKORO_DIR", "~/.cache/aloud/kokoro"))


def kokoro_ready() -> bool:
    d = kokoro_dir()
    if not (os.path.exists(os.path.join(d, KOKORO_MODEL))
            and os.path.exists(os.path.join(d, KOKORO_VOICES))):
        return False
    try:
        import kokoro_onnx  # noqa: F401
        import soundfile  # noqa: F401
    except ImportError:
        return False
    return True


def default_backend() -> str:
    chosen = (os.getenv("ALOUD_TTS") or "").strip().lower()
    if chosen in ("say", "kokoro"):
        return chosen
    if shutil.which("say"):
        return "say"
    if kokoro_ready():
        return "kokoro"
    return "say"


_KOKORO = None


def _kokoro():
    """One model per process. Loading it costs about a second, and the fitting
    loop asks for dozens of sentences per film."""
    global _KOKORO
    if _KOKORO is None:
        import onnxruntime as ort
        from kokoro_onnx import Kokoro

        # Bounded on purpose. Left alone, onnxruntime takes every core on the
        # machine for each sentence, and this runs on shared boxes.
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = int(os.getenv("ALOUD_TTS_THREADS", "4"))
        session = ort.InferenceSession(
            os.path.join(kokoro_dir(), KOKORO_MODEL), opts,
            providers=["CPUExecutionProvider"])
        _KOKORO = Kokoro.from_session(
            session, os.path.join(kokoro_dir(), KOKORO_VOICES))
    return _KOKORO


class Synth:
    """Anything that can turn text into audio and tell you how long it is."""

    def __init__(self, voice: str | None = None, rate: int | None = None,
                 backend: str | None = None):
        self.voice = voice
        self.rate = rate
        self.backend = backend or default_backend()
        # Measured lengths, keyed by the sentence. See `duration`.
        self._measured: dict[str, float] = {}

    @property
    def available(self) -> bool:
        if self.backend == "kokoro":
            return kokoro_ready()
        return bool(shutil.which("say") and shutil.which("ffmpeg"))

    @property
    def name(self) -> str:
        """Which voice spoke, for the track's provenance."""
        if self.backend == "kokoro":
            return f"Kokoro 82M ({self._kokoro_voice()})"
        return f"macOS say ({self.voice or 'system voice'})"

    def _kokoro_voice(self) -> str:
        v = (self.voice or os.getenv("ALOUD_VOICE") or KOKORO_DEFAULT_VOICE)
        return KOKORO_FOR_SAY.get(v.lower(), v)

    def speak(self, text: str, out_dir: str | None = None) -> Spoken:
        text = (text or "").strip()
        if not text:
            return Spoken(text, None, 0.0)
        if not self.available:
            raise RuntimeError("no synthesiser available")
        d = out_dir or tempfile.mkdtemp(prefix="aloud-")
        os.makedirs(d, exist_ok=True)
        stem = os.path.join(d, f"cue-{abs(hash(text)) % (10 ** 10)}")
        wav = stem + ".wav"
        if self.backend == "kokoro":
            self._speak_kokoro(text, wav)
        else:
            self._speak_say(text, stem + ".aiff", wav)
        with wave.open(wav) as w:
            seconds = w.getnframes() / float(w.getframerate())
        self._measured[text] = round(seconds, 3)
        return Spoken(text, wav, round(seconds, 3))

    def _speak_say(self, text: str, aiff: str, wav: str) -> None:
        cmd = ["say", "-o", aiff]
        if self.voice:
            cmd += ["-v", self.voice]
        if self.rate:
            cmd += ["-r", str(self.rate)]
        subprocess.run(cmd + [text], check=True, capture_output=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", aiff,
                        "-ac", "1", "-ar", "16000", wav],
                       check=True, capture_output=True)
        os.remove(aiff)

    def _speak_kokoro(self, text: str, wav: str) -> None:
        import numpy as np
        import soundfile as sf

        speed = (self.rate / SAY_DEFAULT_WPM) if self.rate else 1.0
        voice = self._kokoro_voice()
        lang = "en-gb" if voice.startswith("b") else "en-us"
        samples, sr = _kokoro().create(text, voice=voice, speed=speed, lang=lang)
        # Kokoro pads every utterance with a little silence at each end. Left
        # in, it is time the schedule pays for and the listener hears as
        # nothing, so it comes off before the length is measured.
        samples = np.asarray(samples, dtype=np.float32)
        loud = np.flatnonzero(np.abs(samples) > 0.01)
        if len(loud):
            lead = int(0.03 * sr)
            samples = samples[max(0, loud[0] - lead):loud[-1] + lead]
        sf.write(wav, samples, sr, subtype="PCM_16")

    def duration(self, text: str) -> float:
        """Exact spoken length, audio discarded.

        Measured once per sentence. The fitting loop asks about the same
        candidate more than once, the pipeline measures a cue and then speaks
        it, and synthesis is by far the slowest thing here: the real-voice suite
        alone asked for the same eight sentences fifteen times. Keeping the
        answer is safe because a synthesiser that gave a different length for
        the same sentence would break the schedule whether this cached it or
        not, and it halves how hard a parallel run leans on a speech daemon that
        is one process for the whole machine.
        """
        text = (text or "").strip()
        if text in self._measured:
            return self._measured[text]
        with tempfile.TemporaryDirectory() as d:
            return self.speak(text, out_dir=d).seconds
