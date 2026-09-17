"""Speech synthesis, and the exact duration of what it produced.

The duration of a spoken sentence is the thing the whole schedule depends on,
and it is cheap to know exactly. Calibrating a syllable model against this voice
left a worst-case error of 0.62 seconds, which against a gap of a second and a
half is the difference between a description and an interruption. So the
pipeline measures rather than predicts, and the estimator in budget.py is
demoted to what it is actually good for: guessing a word target before anything
has been written.

`say` is used here because it needs no key and no network, so the pipeline runs
end to end on any Mac. Swap `Synth` for the voice that ships; the contract is
one method that returns audio and its true length.
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


class Synth:
    """Anything that can turn text into audio and tell you how long it is."""

    def __init__(self, voice: str | None = None, rate: int | None = None):
        self.voice = voice
        self.rate = rate
        # Measured lengths, keyed by the sentence. See `duration`.
        self._measured: dict[str, float] = {}

    @property
    def available(self) -> bool:
        return bool(shutil.which("say") and shutil.which("ffmpeg"))

    def speak(self, text: str, out_dir: str | None = None) -> Spoken:
        text = (text or "").strip()
        if not text:
            return Spoken(text, None, 0.0)
        if not self.available:
            raise RuntimeError("no synthesiser available")
        d = out_dir or tempfile.mkdtemp(prefix="aloud-")
        os.makedirs(d, exist_ok=True)
        stem = os.path.join(d, f"cue-{abs(hash(text)) % (10 ** 10)}")
        aiff, wav = stem + ".aiff", stem + ".wav"
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
        with wave.open(wav) as w:
            seconds = w.getnframes() / float(w.getframerate())
        self._measured[text] = round(seconds, 3)
        return Spoken(text, wav, round(seconds, 3))

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
