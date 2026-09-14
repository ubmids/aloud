"""Detection against real speech, which is the only test that counted.

Every other gap test uses a synthetic voice: a stack of pure tones inside the
speech band. It scores 0.99 on the speech-band measure. Real voices score 0.52
to 0.66. So every one of those tests passed with half a point of margin that
does not exist in reality, and two serious faults hid behind that margin:

  - broadband sound (rain, applause, crowd) spreads energy across the speech
    band and scores HIGHER than a human voice, so a band-only detector hears
    dialogue through an entire rainy scene and emits nothing at all
  - a music bed misreads a small fraction of its frames as speech, and that
    scatter fragments a good three second gap into pieces too short to use

Both were invisible until the fixtures were real. This file uses the system
synthesiser for dialogue and realistic beds, and it is the one to run first when
anything in gaps.py changes.
"""
import os
import shutil
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.gaps import find_gaps, load_audio, modulation, speechiness
from aloud.synth import Synth

SR = 16000
SYNTH = Synth()

# Seeded. The beds are noise, and unseeded noise made the recovery figure swing
# between 4.5s and 6.1s from run to run, so the suite went red on nothing having
# changed. A flaky test is worse than no test: it teaches you to rerun instead
# of to look. The voices are already deterministic.
RNG = np.random.default_rng(20260914)


def have_voice():
    if not SYNTH.available:
        print("SKIP no synthesiser on this machine")
        return False
    return True


def voice(text, v=None):
    a, _ = load_audio(Synth(voice=v).speak(text).path)
    return a


def rain(d):
    n = RNG.standard_normal(int(SR * d))
    return np.convolve(n, np.ones(9) / 9, "same") * 0.25


def orchestral(d):
    t = np.arange(int(SR * d)) / SR
    s = np.zeros_like(t)
    for f, a in [(55, .5), (110, .4), (165, .3), (220, .25), (330, .2), (440, .15)]:
        s += a * np.sin(2 * np.pi * f * t)
    return s * 0.35


def room_tone(d):
    return RNG.standard_normal(int(SR * d)) * 0.003


def build():
    # Rebuilt from the same seed every time, so a failure means the detector
    # changed and not that the dice did.
    global RNG
    RNG = np.random.default_rng(20260914)
    parts = [
        ("speech", voice("A man in a grey coat crosses the empty street.", "Samantha")),
        ("rain", rain(4.0)),
        ("speech", voice("He hesitates, then signs the paper.", "Daniel")),
        ("music", orchestral(3.5)),
        ("room", room_tone(2.5)),
        ("speech", voice("The room is empty.")),
    ]
    track, bounds, t = [], [], 0.0
    for name, seg in parts:
        track.append(seg)
        bounds.append((name, t, t + len(seg) / SR))
        t += len(seg) / SR
    return np.concatenate(track), bounds


def test_real_speech_scores_far_lower_than_the_synthetic_fixture():
    if not have_voice():
        return
    scores = []
    for v in (None, "Samantha", "Daniel", "Karen"):
        try:
            scores.append(float(speechiness(voice("The room is empty.", v), SR).mean()))
        except Exception:
            pass
    assert scores, "no voices available"
    assert max(scores) < 0.85, (
        f"real speech scored {max(scores):.2f}; if this ever approaches the "
        "synthetic fixture's 0.99 the fixtures have stopped being realistic")
    print(f"PASS real speech scores {min(scores):.2f} to {max(scores):.2f}, "
          "not the 0.99 the synthetic fixture gives")


def test_broadband_noise_outscores_speech_on_the_band_alone():
    """Why the band measure cannot be the only condition."""
    if not have_voice():
        return
    r = float(speechiness(rain(4.0), SR).mean())
    v = float(speechiness(voice("The room is empty.", "Samantha"), SR).mean())
    assert r > v, f"rain {r:.2f} vs voice {v:.2f}"
    # and the syllable rhythm is what tells them apart
    assert float(modulation(rain(4.0), SR).mean()) < \
        float(modulation(voice("A man crosses the empty street.", "Samantha"), SR).mean())
    print(f"PASS rain scores {r:.2f} on the band against a voice at {v:.2f}, "
          "and the syllable rhythm separates them")


def test_rain_is_a_gap_not_dialogue():
    if not have_voice():
        return
    track, bounds = build()
    gaps = find_gaps(track, SR)
    _, r_start, r_end = next(b for b in bounds if b[0] == "rain")
    assert any(g.start >= r_start - 0.5 and g.end <= r_end + 0.5 for g in gaps), \
        f"no gap found over the rain: {gaps}"
    print("PASS rain reads as a gap, not as dialogue")


def test_no_gap_ever_overlaps_real_dialogue():
    """The one thing this system must not do.

    A cue landing on a line removes information the listener already had, which
    is worse than saying nothing. Two earlier smoothing designs leaked here: a
    symmetric filter shrank lines from both ends by 60ms, and dropping short
    runs outright deleted the quiet tail of a line and leaked half a second.
    """
    if not have_voice():
        return
    track, bounds = build()
    gaps = find_gaps(track, SR)
    speech = [(a, b) for n, a, b in bounds if n == "speech"]
    overlap = sum(max(0.0, min(g.end, sb) - max(g.start, sa))
                  for g in gaps for sa, sb in speech)
    assert overlap == 0.0, f"{overlap:.3f}s of dialogue was inside a gap: {gaps}"
    print(f"PASS {len(gaps)} gap(s), none touching dialogue")


def test_enough_of_the_quiet_is_still_recovered():
    """Safety costs gap time, and the cost has to stay bounded. Closing the
    speech mask before opening it also joins scattered frames inside a music
    bed, so some usable quiet is given up. Roughly 60% of the non-speech time
    survives as gaps, which is the measured trade, not an aspiration."""
    if not have_voice():
        return
    track, bounds = build()
    gaps = find_gaps(track, SR)
    quiet = sum(b - a for n, a, b in bounds if n != "speech")
    got = sum(g.duration for g in gaps)
    assert got >= quiet * 0.5, f"only {got:.1f}s of {quiet:.1f}s recovered"
    assert got <= quiet, f"recovered {got:.1f}s of {quiet:.1f}s, which is impossible"
    print(f"PASS {got:.1f}s of {quiet:.1f}s of quiet recovered as usable gaps")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
