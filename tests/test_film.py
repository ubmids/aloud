"""A film in, a described film out, with nothing real underneath it.

`aloud/pipeline.py` is the module that runs the other five in order, decides
what to do when the describer fails partway through a film, and mixes the
result back into the audio. Every other suite here tests a stage on its own and
none of them imported this one, so Mutiny scored it at 3%, which is the score an
untested module gets.

The film is built here out of colour and tones, the describer is a stub and the
voice is a stub with a duration model this file owns, so the whole file needs no
key, no network and no speech daemon. What it does need is ffmpeg, because the
thing being tested is the pipeline's own use of it.
"""
import atexit
import os
import subprocess
import shutil
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.gaps import find_gaps, load_audio
from aloud.pipeline import describe_film, mix, stub_captioner
from aloud.synth import Spoken

SR = 16000
# Per-process, not a fixed path. A shared /tmp file makes the suite
# non-hermetic: run two copies at once, as any mutation tester or parallel CI
# does, and they race on the same file.
FILM = os.path.join(tempfile.gettempdir(), f"aloud_test_reel_{os.getpid()}.mp4")


def voiced(seconds, amp=1.0):
    """Speech band energy opening and closing at a syllable rate."""
    t = np.arange(int(SR * seconds)) / SR
    sig = sum(np.sin(2 * np.pi * f * t) * a
              for f, a in [(220, .5), (600, .7), (1400, .5), (2600, .3)])
    return (amp * sig * (0.4 + 0.3 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)


def score(seconds):
    """Loud, and nothing in it is talking. This is a gap."""
    t = np.arange(int(SR * seconds)) / SR
    return (0.5 * np.sin(2 * np.pi * 90 * t)
            + 0.35 * np.sin(2 * np.pi * 140 * t)).astype(np.float32)


def hush(seconds):
    return (np.random.default_rng(7).standard_normal(int(SR * seconds))
            * 0.0015).astype(np.float32)


def write_wav(path, samples):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def make_film():
    """Nine and a half seconds: three shots, two lines, and two gaps.

    The first gap is a loud score and the second is room tone, because the duck
    under a cue is measured from the film beneath it and a single fixed level
    was what made the description over the music inaudible.
    """
    if os.path.exists(FILM):
        return True
    if not shutil.which("ffmpeg"):
        return False
    audio = os.path.join(tempfile.gettempdir(), f"aloud_test_bed_{os.getpid()}.wav")
    write_wav(audio, np.concatenate([voiced(1.5), score(3.0), voiced(1.0),
                                     hush(3.0), voiced(1.0)]))
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", "color=c=navy:s=320x180:d=1.2",
         "-f", "lavfi", "-i", "color=c=darkgreen:s=320x180:d=3.8",
         "-f", "lavfi", "-i", "color=c=maroon:s=320x180:d=4.5",
         "-i", audio,
         "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
         "-map", "[v]", "-map", "3:a", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-shortest", FILM], check=True)
    os.remove(audio)
    atexit.register(lambda: os.path.exists(FILM) and os.remove(FILM))
    return True


class FakeVoice:
    """A voice that writes real audio of a length this file decides.

    Deliberately not the estimator in budget.py. If the stub and the code under
    test shared a duration model, a change to that model would move the fixture
    and the expectation together and the test would never notice.
    """

    def __init__(self, per_word=0.22, fixed=0.25):
        self.per_word, self.fixed = per_word, fixed
        self.spoken = []

    def duration(self, text):
        words = len((text or "").split())
        return self.fixed + self.per_word * words if words else 0.0

    def speak(self, text, out_dir=None):
        text = (text or "").strip()
        seconds = self.duration(text)
        if not text:
            return Spoken(text, None, 0.0)
        d = out_dir or tempfile.mkdtemp(prefix="aloud-test-")
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, f"cue-{len(self.spoken)}.wav")
        write_wav(path, voiced(seconds, amp=0.6))
        self.spoken.append(text)
        return Spoken(text, path, round(seconds, 3))


def described(**kw):
    """The pipeline, run on the film with nothing real underneath it."""
    out = os.path.join(tempfile.gettempdir(), f"aloud_test_out_{os.getpid()}")
    shutil.rmtree(out, ignore_errors=True)
    kw.setdefault("captioner", stub_captioner)
    kw.setdefault("synth", FakeVoice())
    return describe_film(FILM, out_dir=out, **kw), out


def test_no_cue_in_a_finished_track_lands_on_dialogue():
    """The claim the whole product rests on, made end to end for the first time.
    Every stage is tested on its own and the order they run in is not: generate
    before you know the gap and the description no longer fits the hole it was
    written for. A cue that overlaps a line removes information the listener
    already had, which is worse than saying nothing at all."""
    if not make_film():
        print("SKIP no ffmpeg")
        return
    voice = FakeVoice()
    result, out = described(synth=voice)
    try:
        assert result.track.cues, f"nothing was described: {result.skipped}"
        # The voice it was handed is the voice it used. Falling back to the
        # machine's own synthesiser instead would build the whole schedule out
        # of durations belonging to a voice nobody chose.
        assert voice.spoken == [c.text for c in result.track.cues], voice.spoken
        assert result.track.validate(result.gaps) == [], \
            result.track.validate(result.gaps)
        for c in result.track.cues:
            inside = [g for g in result.gaps if g.start <= c.start and c.end <= g.end]
            assert inside, f"{c.start:.2f}-{c.end:.2f}s is not inside a gap"
            assert c.text.strip(), c
            # And the audio really is short enough for the window it was given,
            # which is the claim a validated track cannot make by itself.
            audio, sr = load_audio(c.audio)
            assert len(audio) / sr <= c.duration + 0.01, (
                f"{len(audio) / sr:.2f}s of speech in a {c.duration:.2f}s cue")
        print(f"PASS {len(result.track.cues)} cue(s), every one inside its gap")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_a_describer_that_fails_costs_that_gap_and_not_the_film():
    """A rate limit, a refused image or a timeout is a normal afternoon, and the
    right answer is the one a gap with nothing to say already gets: leave it
    silent and carry on. Without this the first failure ends the film, and the
    viewer loses every description after it rather than one."""
    if not make_film():
        print("SKIP no ffmpeg")
        return
    calls = []

    def flaky(frame, words):
        calls.append(frame)
        if len(calls) == 1:
            raise RuntimeError("429 slow down")
        # Not the stub's words: the pipeline refuses a sentence about the film
        # ("The scene changes...") from anything but the stub itself.
        return " ".join("Snow drifts across an empty courtyard toward a tall "
                        "iron gate".split()[:max(2, words)]) + "."

    result, out = described(captioner=flaky)
    try:
        assert len(calls) > 1, "the film stopped at the first failure"
        assert result.track.cues, "one failed describer cost every description"
        assert any("the describer failed" in why and "RuntimeError" in why
                   for _gap, why in result.skipped), result.skipped
        assert result.track.validate(result.gaps) == []
        print("PASS a failed describer costs one gap:", result.skipped[0][1])
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_a_gap_nothing_will_fit_in_is_left_silent():
    """Silence is a valid description. A writer that will not come down to the
    size of the gap has to be dropped rather than squeezed in, because the only
    way to make it fit is to run over the line at the end of the gap."""
    if not make_film():
        print("SKIP no ffmpeg")
        return
    huge = ("A man in a grey overcoat crosses the empty station concourse "
            "towards the departure board while the snow keeps falling")

    result, out = described(captioner=lambda frame, words: huge)
    try:
        assert result.track.cues == [], result.track.cues
        assert result.skipped, "a gap was neither described nor reported"
        assert any("nothing useful fitted" in why for _gap, why in result.skipped), \
            result.skipped
        print("PASS a description that will not fit leaves the gap silent")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_the_stub_describer_never_pretends_to_have_seen_the_frame():
    """It exists so the pipeline runs with no key, which means it runs in front
    of people. A stub that wrote plausible descriptions would make a broken
    describer look like a working one, and a missing key would ship as a feature
    nobody noticed was dead."""
    assert stub_captioner("/no/such/frame.jpg", 8).startswith(
        "The scene changes"), stub_captioner("/no/such/frame.jpg", 8)
    # It still answers the word target it was given, because that target is the
    # measured size of the gap and the rest of the pipeline believes it.
    assert len(stub_captioner("f.jpg", 12).split()) == 12
    assert len(stub_captioner("f.jpg", 4).split()) == 4
    # Two words is the floor. A zero word target must not produce a cue that is
    # a full stop and nothing else.
    for target in (0, 1, 2):
        assert len(stub_captioner("f.jpg", target).split()) == 2, target
    assert stub_captioner("f.jpg", 6).endswith("."), stub_captioner("f.jpg", 6)
    print("PASS the stub is obviously a stub and still hits its word target")


def test_the_description_lands_where_the_track_says_it_does():
    """The mixed film is the artefact this gets judged on, and every cue is put
    into it by one delay written in milliseconds. Get that wrong and the
    descriptions play at the wrong moments, the first one landing over the
    opening line. The track would still validate perfectly, because nothing in
    it describes the mix: the only way to know is to listen to the output, which
    is what this does."""
    if not make_film():
        print("SKIP no ffmpeg")
        return
    result, out = described()
    try:
        mixed = os.path.join(out, "described.mp4")
        mix(FILM, result, mixed)
        audio, sr = load_audio(mixed)

        def level(start, end):
            seg = audio[int(start * sr):int(end * sr)]
            return float(np.sqrt((seg ** 2).mean()))

        # The last cue sits over room tone, so anything audible in its window is
        # the description and the quiet either side of it is the film.
        cue = result.track.cues[-1]
        during = level(cue.start + 0.05, cue.end - 0.05)
        after = level(cue.end + 0.1, cue.end + 0.6)
        assert during > 0.05, f"nothing is being spoken at {cue.start:.2f}s"
        assert after < during / 10, (
            f"the description is still going {after:.4f} after {cue.end:.2f}s")
        print(f"PASS the cue at {cue.start:.2f}s is audible there and nowhere else")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_each_cue_is_ducked_against_the_film_underneath_it():
    """One fixed ducking level was the first version and it failed where it
    mattered. A flat drop is plenty under room tone and nothing under a score,
    so the description over the music came out quieter than the music and was
    simply not there. The duck has to be measured from the film beneath each
    cue, which means a loud passage ducks hard and a quiet one is left alone."""
    if not make_film():
        print("SKIP no ffmpeg")
        return
    result, out = described()
    try:
        if len(result.track.cues) < 2:
            print("SKIP the film produced one cue, not two")
            return
        mixed = os.path.join(out, "described.mp4")
        mix(FILM, result, mixed)
        assert os.path.exists(mixed)
        assert result.ducks and len(result.ducks) == len(result.track.cues)

        gains = dict(result.ducks)
        loud, quiet = sorted(gains)[0], sorted(gains)[1]
        assert gains[loud] < gains[quiet], (
            f"the score at {loud}s ducked to {gains[loud]} and the room tone at "
            f"{quiet}s to {gains[quiet]}, which is the wrong way round")
        assert gains[quiet] == 1.0, (
            f"room tone was ducked to {gains[quiet]} for no reason")
        for _at, g in result.ducks:
            # Never silence the film entirely: -24dB is a floor, not a target.
            assert 10 ** (-24.0 / 20.0) <= g <= 1.0, g
        print(f"PASS the score ducks to {gains[loud]}, the room tone to "
              f"{gains[quiet]}")
    finally:
        shutil.rmtree(out, ignore_errors=True)


def test_a_describer_that_has_gone_away_stops_the_run():
    """A model server died a few minutes into a film and the run carried on,
    skipping every gap after it, and wrote a track that was silent from there
    to the end. A run of failures now stops the film with nothing written."""
    if not make_film():
        print("SKIP no ffmpeg")
        return

    def dead(frame, words):
        raise ConnectionError("connection refused")

    try:
        described(captioner=dead, max_failures=1)
        raise AssertionError("a dead describer produced a finished track")
    except RuntimeError as e:
        assert "in a row" in str(e), e
    print("PASS a describer that has gone away stops the run")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
