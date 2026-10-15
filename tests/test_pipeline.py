"""The two things Aloud has to get right.

Finding a hole in the dialogue, and fitting something useful inside it without
ever landing on top of a line.
"""
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.budget import DANGLING, fit_generated, fit_measured, words_for
from aloud.gaps import find_gaps, speechiness
from aloud import synth as synth_mod
from aloud.synth import Synth

SR = 16000


def speech(dur):
    t = np.arange(int(SR * dur)) / SR
    sig = sum(np.sin(2 * np.pi * f * t) * a
              for f, a in [(220, .5), (600, .7), (1400, .5), (2600, .3)])
    return (sig * (0.4 + 0.3 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)


def music(dur):
    t = np.arange(int(SR * dur)) / SR
    return (0.5 * np.sin(2 * np.pi * 90 * t) + 0.35 * np.sin(2 * np.pi * 140 * t)
            + 0.2 * np.sin(2 * np.pi * 8000 * t)).astype(np.float32)


def quiet(dur):
    # Seeded. An unseeded fixture makes the suite answer differently on
    # different runs, and a mutation tester reads that as a finding about the
    # code rather than about the noise it was handed.
    return (np.random.default_rng(31).standard_normal(int(SR * dur))
            * 0.0015).astype(np.float32)


def test_loud_music_is_a_gap_not_dialogue():
    """The whole reason this uses a speech band instead of a loudness threshold.
    Music is loud and is still a hole a description can live in."""
    track = np.concatenate([speech(2.0), music(3.0), speech(1.5)])
    gaps = find_gaps(track, SR)
    assert len(gaps) == 1, gaps
    assert 1.9 < gaps[0].start < 2.3 and 4.6 < gaps[0].end < 5.1, gaps
    print("PASS loud music reads as a gap:", gaps[0])


def test_silence_and_music_both_found():
    track = np.concatenate([speech(2.0), music(3.0), speech(1.5),
                            quiet(2.5), speech(1.0)])
    gaps = find_gaps(track, SR)
    assert len(gaps) == 2, gaps
    print("PASS both kinds of gap found:", gaps)


def test_detection_does_not_depend_on_unrelated_content():
    """Regression. The noise floor was once a percentile of the track's own
    loudness, so whether a line of dialogue registered as speech depended on how
    much quiet material happened to sit elsewhere in the file. A fixture with a
    silent passage passed while the same code reported a whole film as one gap.
    The same segment must score the same regardless of its neighbours."""
    short = np.concatenate([speech(2.0), music(3.0), speech(1.5)])
    long = np.concatenate([speech(2.0), music(3.0), speech(1.5),
                           quiet(2.5), speech(1.0)])
    a, b = find_gaps(short, SR), find_gaps(long, SR)
    assert a, "speech went undetected without a quiet passage present"
    assert abs(a[0].start - b[0].start) < 0.01, (a, b)
    assert abs(a[0].end - b[0].end) < 0.01, (a, b)
    print("PASS detection is independent of unrelated content")


def test_short_gaps_are_rejected():
    """A third of a second is not a gap, it is a breath."""
    track = np.concatenate([speech(2.0), quiet(0.35), speech(2.0)])
    assert find_gaps(track, SR) == []
    print("PASS sub-second gaps rejected")


def test_no_speech_at_all_is_one_long_gap():
    assert len(find_gaps(quiet(5.0), SR)) == 1
    print("PASS a silent passage is one gap")


def test_generated_description_never_overruns():
    """The real path: length is asked for, then verified by measurement."""
    s = Synth()
    if not s.available:
        print("SKIP no synthesiser on this machine")
        return
    variants = {
        22: "A man in a grey coat crosses the empty street as snow begins to "
            "fall on the rooftops behind him.",
        12: "A man in a grey coat crosses the empty street in snow.",
        7: "A man crosses the snowy street.",
        4: "A man crosses.",
    }

    def describe(target):
        return variants[min(variants, key=lambda k: abs(k - target))]

    for gap in (6.0, 3.0, 1.6, 1.4):
        f = fit_generated(describe, gap, s)
        if gap < 2.0 and not f.text:
            # Whether "A man crosses." fits a second and a half depends on
            # the voice: Kokoro says it in 1.2s, the system voice on some
            # macOS releases does not. Silence is the contract's answer when
            # nothing fits; what must never happen is an overrun.
            assert not f.fits and f.seconds == 0.0, f
            print(f"PASS gap {gap}s -> silent, nothing fits with {s.name}")
            continue
        assert f.fits and f.text, f
        real = s.duration(f.text)
        assert real <= f.budget, f"{real}s in a {f.budget}s budget: {f.text!r}"
        print(f"PASS gap {gap}s -> {real:.2f}s of {f.budget}s: {f.text!r}")


def test_truncation_refuses_to_dangle():
    """'A man in a grey.' is inside budget and says nothing. Better to be silent.

    The rule is structural rather than lexical: cut at punctuation or not at all.
    A stop list cannot catch this, because the offending word is an ordinary
    adjective.
    """
    s = Synth()
    if not s.available:
        print("SKIP no synthesiser on this machine")
        return
    no_clauses = ("A man in a grey coat crosses the empty street as snow "
                  "begins to fall on the rooftops behind him.")
    for gap in (3.0, 1.6, 1.4):
        f = fit_measured(no_clauses, gap, s)
        assert f.text == "" and not f.fits, f
    print("PASS refuses to mangle a sentence with no clause boundary")

    clauses = "Snow fills the courtyard, thick and steady, burying the parked cars."
    f = fit_measured(clauses, 2.6, s)
    assert f.text == "Snow fills the courtyard.", f.text
    last = f.text.rstrip(".").split()[-1].lower()
    assert last not in DANGLING
    print("PASS cuts cleanly where a clause boundary exists:", repr(f.text))


def test_a_gap_too_small_to_fill_is_not_reported():
    """MIN_GAP_S is measured against what the voice can actually say. A 1 second
    gap holds 0.85s of speech after headroom, and the shortest useful
    description runs longer than that, so reporting it only wastes the
    describer's time on something that can never be scheduled."""
    track = np.concatenate([speech(2.0), quiet(1.0), speech(2.0)])
    assert find_gaps(track, SR) == []
    track = np.concatenate([speech(2.0), quiet(2.2), speech(2.0)])
    assert len(find_gaps(track, SR)) == 1
    print("PASS gaps too small to fill are not reported")


def test_the_measured_duration_is_the_length_of_the_audio():
    """The whole schedule is built on this one number and nothing checks it
    afterwards. Rounded to the nearest second, a 2.4s description is handed a
    2.0s window: the voice is still going when the window closes, and what
    closes it is the next line of dialogue. Every stage after this believes the
    duration it was given, so there is nothing downstream that could notice."""
    s = Synth()
    if not s.available:
        print("SKIP no synthesiser on this machine")
        return
    spoken = s.speak("A man in a grey coat crosses the empty street.")
    try:
        with wave.open(spoken.path) as w:
            exact = w.getnframes() / float(w.getframerate())
        assert abs(exact - round(exact)) > 0.01, (
            f"this voice landed on {exact}s, a whole second, so this test "
            "cannot tell a rounded duration from a real one")
        assert abs(spoken.seconds - exact) <= 0.0005, (spoken.seconds, exact)
    finally:
        os.path.exists(spoken.path) and os.remove(spoken.path)
    print(f"PASS the cue is measured at {spoken.seconds}s, the length of its audio")


def test_the_same_sentence_is_only_ever_measured_once():
    """The fitting loop asks about the same candidate more than once and a cue
    is measured before it is spoken, so a sentence is synthesised repeatedly to
    answer a question that cannot have changed. The length that comes back the
    second time still has to be the one that was measured, because that number
    is what the cue is scheduled against."""
    s = Synth()
    if not s.available:
        print("SKIP no synthesiser on this machine")
        return
    text = "A man crosses the empty street."
    measured = s.duration(text)
    assert measured > 0.0, measured

    # Take the voice away. A second ask still has to answer, and answer the
    # same, which it can only do from what it measured the first time.
    class _NoTools:
        @staticmethod
        def which(_name):
            return None

    real = synth_mod.shutil
    synth_mod.shutil = _NoTools
    try:
        assert s.duration(text) == measured, "the second answer was a new one"
    finally:
        synth_mod.shutil = real
    print(f"PASS {text!r} is measured once, at {measured}s")


def test_word_target_shrinks_with_the_gap():
    assert words_for(6.0) > words_for(3.0) > words_for(1.5) >= 0
    print(f"PASS word target tracks gap size: "
          f"{words_for(6.0)}, {words_for(3.0)}, {words_for(1.5)}")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
