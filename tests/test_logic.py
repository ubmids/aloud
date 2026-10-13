"""The core logic, with nothing slow underneath it.

Every other suite here shells out: `say` for a real voice, ffmpeg for real
audio. That is the right way to test a detector and it costs thirty seconds a
run, which is fine once and impossible when something has to run the suite
hundreds of times. Mutation testing does exactly that, and the modules that
carry the safety property are the ones it could not reach.

So this file is the fast, hermetic half. The synthesiser is a stub with a known
duration model, the audio is a handful of tones, and the whole file runs in
about a second. It is not a replacement for the real fixtures: a synthetic voice
scores 0.99 on the speech band where a real one scores 0.55, and pretending
otherwise is how the two faults in test_real_audio.py hid for so long. It is the
part that can be run on every keystroke, and against every mutant.
"""
import os
import shutil
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud import synth as synth_mod
from aloud.budget import (DANGLING, ESTIMATE_ERROR_S, FIXED_COST_S, HEADROOM,
                          PAUSE_COMMA_S, PAUSE_STOP_S, SECONDS_PER_SYLLABLE,
                          budget_for, fit, fit_generated, fit_measured,
                          speech_seconds, syllables, words_for)
from aloud.calibrate import features
from aloud.gaps import (MIN_GAP_S, Gap, _runs, _smooth, find_gaps, load_audio,
                        modulation, speechiness)
from aloud.synth import Spoken, Synth

SR = 16000
FRAME_MS = 20.0


class FakeSynth:
    """A voice with a duration model this file owns.

    Deliberately not `speech_seconds`. If the stub and the code under test
    shared an estimator, a change to that estimator would move the fixture and
    the expectation together and the test would never notice. This one is a
    fixed cost plus a cost per word, which is wrong about English and exactly
    right for asking whether the fitting logic believes what it measures.
    """

    def __init__(self, per_word: float = 0.40, fixed: float = 0.30):
        self.per_word, self.fixed = per_word, fixed
        self.asked = []

    def duration(self, text: str) -> float:
        words = len((text or "").split())
        self.asked.append(text)
        return self.fixed + self.per_word * words if words else 0.0


# --- the duration estimate ---------------------------------------------------

def test_syllables_survives_the_words_that_break_a_naive_counter():
    """The syllable count is the only thing between a gap and a word target, so
    the cases that are wrong in an obvious direction matter. Silent e is the
    common one, and the three endings that are not a silent e are the reason the
    rule has an exception list at all."""
    assert syllables("grade") == 1, "silent e was counted"
    assert syllables("little") == 2, "le is not a silent e"
    assert syllables("agree") == 2, "ee is not a silent e"
    assert syllables("crosses") == 2
    assert syllables("arcade") == 2, "the silent e took more than one beat"
    assert syllables("the") == 1, "a one syllable word lost its only vowel"
    assert syllables("rhythm") == 1, "y carries the syllable here"
    assert syllables("tsk") == 1, "every real word takes at least one beat"
    assert syllables("Man") == syllables("man"), "case changed the count"
    assert syllables("...") == 0, "punctuation is not a syllable"
    print("PASS syllables handles silent e, le/ee, y, and punctuation")


def test_nothing_to_say_takes_no_time():
    """A gap with no description in it must cost zero, not a fixed overhead.
    Otherwise silence is scheduled as if it were speech."""
    assert speech_seconds("") == 0.0
    assert speech_seconds("   ") == 0.0
    assert speech_seconds(None) == 0.0
    print("PASS an empty description is zero seconds, not a fixed cost")


def test_the_estimate_stays_inside_the_residual_the_calibration_claims():
    """CALIBRATION.md measures these seven phrases against the reference voice
    and puts the worst residual at 0.62s. That number is not decoration: it is
    the margin `fit` holds back, so if the estimator drifts outside it the
    margin stops being enough and the estimate-only path starts scheduling
    overruns."""
    measured = {"He waits.": 0.64, "A man.": 0.65, "She turns.": 0.77,
                "Snow falls.": 0.91, "Nothing moves.": 0.99,
                "A man crosses.": 1.10, "A door opens.": 1.19}
    worst = max(abs(speech_seconds(p) - s) for p, s in measured.items())
    assert worst <= ESTIMATE_ERROR_S, (
        f"worst residual {worst:.2f}s against a documented {ESTIMATE_ERROR_S}s")
    print(f"PASS the estimator is within {worst:.2f}s of the measured voice")


def test_the_calibration_fits_the_model_that_ships():
    """`calibrate.py` prints the constants at the top of budget.py, and it can
    only do that honestly if it is fitting the same five terms the estimator is
    made of. Change the features on one side and the fit still converges, still
    reports a small residual, and hands over numbers for a model nobody runs.
    Every duration in the pipeline then comes from constants calibrated against
    the wrong thing, and the error is invisible because the arithmetic is fine
    on both sides."""
    weights = [FIXED_COST_S, SECONDS_PER_SYLLABLE,
               SECONDS_PER_SYLLABLE,          # a digit is charged a syllable
               PAUSE_COMMA_S, PAUSE_STOP_S]
    for phrase in ("He turns.",
                   "The clock reads 3:15.",
                   "She waits. He does not answer.",
                   "Snow, thick and steady; it fills the courtyard.",
                   "The train to platform 9 is delayed by 40 minutes."):
        row = features(phrase)
        assert len(row) == len(weights), row
        modelled = sum(f * w for f, w in zip(row, weights))
        assert abs(modelled - speech_seconds(phrase)) <= 1e-9, (
            f"{phrase!r}: the calibration would fit {modelled:.3f}s and the "
            f"estimator charges {speech_seconds(phrase):.3f}s")
    print("PASS the calibration fits the same five terms the estimator uses")


def test_a_longer_sentence_costs_proportionally_more():
    """A fixed cost per utterance is not a model of speech. Twenty syllables
    must cost several times what five do, or the word target is a constant
    wearing a formula."""
    short = "A man waits."
    long = ("A man in a grey overcoat crosses the empty station concourse "
            "towards the departure board.")
    assert speech_seconds(long) > 3 * speech_seconds(short), (
        speech_seconds(long), speech_seconds(short))
    print(f"PASS {speech_seconds(long):.2f}s against {speech_seconds(short):.2f}s")


def test_punctuation_buys_real_pauses():
    """The synthesiser inserts them whether the budget accounted for them or
    not, and a full stop is a longer pause than a comma."""
    plain = speech_seconds("snow falls on the roof")
    comma = speech_seconds("snow falls, on the roof")
    semi = speech_seconds("snow falls; on the roof")
    stop = speech_seconds("snow falls. on the roof")
    assert comma > plain, "a comma cost nothing"
    assert semi > plain, "a semicolon cost nothing"
    assert stop > comma, "a full stop cost no more than a comma"
    print(f"PASS pauses cost time: {plain:.2f} < {comma:.2f} < {stop:.2f}")


def test_digits_are_spoken_one_at_a_time():
    """"17:42" is five characters and takes about a second to say. A character
    count cannot see that and a description full of numbers overruns."""
    assert speech_seconds("17:42") > speech_seconds("at")
    assert speech_seconds("1942") > speech_seconds("19")
    # The module puts "17:42" at about a second. A digit costing a syllable is
    # the claim; a digit costing five syllables would refuse every description
    # with a time in it.
    assert 0.7 <= speech_seconds("17:42") <= 1.5, speech_seconds("17:42")
    print("PASS a number costs more than a short word of the same length")


# --- the budget --------------------------------------------------------------

def test_the_budget_never_fills_the_whole_gap():
    """Headroom is the difference between a description and an interruption. A
    cue that begins as the previous line ends and finishes as the next begins is
    inside its gap and still sounds like talking over the film."""
    for gap in (1.5, 3.0, 12.0):
        b = budget_for(gap)
        assert 0.0 < b < gap, f"a {gap}s gap was given a {b}s budget"
        assert b >= gap * 0.5, "headroom swallowed the gap"
    print("PASS the budget always leaves the edges of the gap alone")


def test_a_gap_of_no_length_has_no_budget():
    """Negative and zero gaps reach here from rounding at the ends of a film,
    and a negative budget would make every description look like it fits."""
    assert budget_for(0.0) == 0.0
    assert budget_for(-2.0) == 0.0
    assert words_for(-2.0) == 0 and words_for(0.0) == 0
    assert words_for(0.3) == 0, "a third of a second was given a word target"
    print("PASS a gap with no room in it gets no budget and no word target")


def test_every_gap_worth_reporting_is_worth_a_description():
    """MIN_GAP_S and the two word floor in `fit_generated` have to agree. If the
    detector reports a gap the word target cannot fill, the describer is never
    called and the gap is silently wasted, which is the failure MIN_GAP_S was
    measured to prevent in the first place."""
    assert words_for(MIN_GAP_S) >= 2, (
        f"the shortest reportable gap ({MIN_GAP_S}s) asks for "
        f"{words_for(MIN_GAP_S)} words, and fit_generated gives up below two")
    print(f"PASS the shortest gap worth reporting asks for "
          f"{words_for(MIN_GAP_S)} words")


def test_the_word_target_tracks_the_gap_in_both_directions():
    assert words_for(8.0) > words_for(4.0) > words_for(2.0) > 0
    assert words_for(3.0, headroom=0.5) < words_for(3.0, headroom=0.85), \
        "less headroom did not buy more words"
    print("PASS the word target follows the gap and the headroom")


def test_the_word_target_is_a_length_a_describer_can_actually_hit():
    """The target exists so the writer aims at the right size instead of being
    cut afterwards. If it asks for more words than the gap can hold, every
    description comes back over budget and the truncation path, which is allowed
    to return nothing at all, runs on every single cue."""
    passage = ("a man in a grey coat crosses the empty street as snow begins "
               "to fall on the rooftops behind him and the lights come on "
               "along the far side").split()
    for gap in (1.5, 2.0, 3.0, 4.0, 6.0, 10.0):
        n = words_for(gap)
        assert n <= len(passage), "the fixture ran out of words"
        written = " ".join(passage[:n]).capitalize() + "."
        assert speech_seconds(written) <= budget_for(gap), (
            f"a {gap}s gap asked for {n} words, which is "
            f"{speech_seconds(written):.2f}s against a {budget_for(gap):.2f}s "
            "budget")
    print("PASS a description of the requested length fits the gap it came from")


# --- fitting by measurement --------------------------------------------------

def test_a_measured_fit_is_never_longer_than_its_budget():
    """The safety property, stated in seconds. Anything reported as fitting has
    to be verifiably inside the budget when spoken, for every gap, not on
    average."""
    s = FakeSynth()
    text = ("Snow fills the courtyard, thick and steady, burying the parked "
            "cars and the road beyond.")
    for gap in (1.5, 2.0, 2.6, 3.5, 5.0, 8.0, 20.0):
        f = fit_measured(text, gap, s)
        if f.fits:
            assert f.text, "a fit with no text claimed to fit"
            assert s.duration(f.text) <= f.budget + 1e-9, (gap, f)
            assert f.budget < gap, (gap, f.budget)
    print("PASS nothing that claims to fit is longer than the gap allows")


def test_a_measured_fit_that_cannot_be_trimmed_says_nothing():
    """A sentence with no clause boundary cannot be shortened without cutting
    inside a phrase, and "A man in a grey." is inside budget and says nothing.
    Silence is a valid description."""
    s = FakeSynth()
    text = ("A man in a grey coat crosses the empty street as snow begins to "
            "fall on the rooftops behind him.")
    f = fit_measured(text, 2.0, s)
    assert f.text == "" and not f.fits and f.trimmed, f
    print("PASS an untrimmable sentence is dropped rather than mangled")


def test_a_measured_fit_cuts_at_the_clause_and_marks_itself_trimmed():
    """The caller needs to know it was cut. A trimmed description that reports
    itself untouched is how a half-described shot looks like a whole one."""
    s = FakeSynth()
    text = "Snow fills the courtyard, thick and steady, burying the parked cars."
    f = fit_measured(text, 2.5, s)
    assert f.fits and f.trimmed, f
    assert f.text == "Snow fills the courtyard.", f.text
    # A clause that still fits must be kept. Dropping two at once throws away
    # information that had room.
    roomier = fit_measured(text, 4.0, s)
    assert roomier.text == "Snow fills the courtyard, thick and steady.", roomier
    whole = fit_measured(text, 30.0, s)
    assert whole.fits and not whole.trimmed, whole
    assert whole.text == text
    print("PASS a cut description says it was cut, an untouched one does not")


def test_no_description_ever_ends_on_a_dangling_word():
    """"A man in a grey coat crosses the." is inside budget and leaves the
    listener waiting for a noun that never arrives, which is worse than silence
    because they now believe they missed something."""
    s = FakeSynth()
    texts = [
        "Snow fills the courtyard, thick and steady, burying the parked cars.",
        "He stops at the door, hesitates, then turns back to the empty room.",
        "A man in a grey coat crosses the street as the snow begins to fall.",
    ]
    for text in texts:
        for gap in (1.4, 1.8, 2.2, 2.6, 3.0, 4.0, 6.0):
            for got in (fit_measured(text, gap, s).text, fit(text, gap).text):
                if not got:
                    continue
                last = got.rstrip(".").split()[-1].strip(",;").lower()
                assert last not in DANGLING, (gap, got)
    print("PASS no trimmed description ends on a dangling word")


def test_a_measured_fit_stops_asking_eventually():
    """A synthesiser that never gets shorter must not spin. Every call costs a
    real subprocess in production."""
    class Stubborn:
        def __init__(self):
            self.calls = 0

        def duration(self, text):
            self.calls += 1
            return 99.0

    s = Stubborn()
    f = fit_measured("A man crosses, and stops, and waits.", 2.0, s,
                     max_rounds=3)
    assert not f.fits and f.text == ""
    assert s.calls <= 3, f"{s.calls} synthesiser calls for max_rounds=3"
    print(f"PASS fitting gave up after {s.calls} calls")


# --- fitting by asking for the right size ------------------------------------

def test_the_describer_is_asked_for_something_smaller_after_an_overrun():
    """The point of the generated path: length is a constraint handed to the
    writer, not damage done afterwards. If the second ask is not smaller than
    the first, the loop is just three identical attempts."""
    s = FakeSynth()
    asks = []

    def describe(target):
        asks.append(target)
        return " ".join(["word"] * 40)

    fit_generated(describe, 4.0, s)
    assert len(asks) > 1, "the describer was asked once and given up on"
    assert asks[1] < asks[0], f"the second ask was not smaller: {asks}"
    print(f"PASS the ask shrinks after an overrun: {asks}")


def test_a_description_that_will_not_shrink_is_dropped_not_squeezed_in():
    s = FakeSynth()
    f = fit_generated(lambda n: " ".join(["word"] * 40), 3.0, s)
    assert not f.fits and f.text == "", f
    print("PASS a writer that ignores the budget gets nothing scheduled")


def test_a_gap_too_small_for_two_words_never_reaches_the_describer():
    """Describing costs a vision call. A gap that cannot hold two words cannot
    hold a description, so asking for one spends money to be thrown away."""
    s = FakeSynth()
    calls = []

    def describe(target):
        calls.append(target)
        return "A man."

    for gap in (0.4, 0.7):
        assert words_for(gap) < 2, f"fixture: {gap}s asks for {words_for(gap)}"
        f = fit_generated(describe, gap, s)
        assert calls == [], f"the describer was called for a {gap}s gap: {calls}"
        assert not f.fits
    print("PASS a gap too small to fill does not cost a describer call")


def test_a_generated_description_that_fits_is_not_marked_trimmed():
    s = FakeSynth()
    f = fit_generated(lambda n: "A man crosses the empty street.", 6.0, s)
    assert f.fits and not f.trimmed, f
    assert f.seconds <= f.budget
    print("PASS a description that fits first time is reported untouched")


def test_a_describer_that_returns_nothing_is_not_treated_as_a_description():
    s = FakeSynth()
    f = fit_generated(lambda n: "", 6.0, s)
    assert not f.fits and f.text == "", f
    print("PASS an empty description is not scheduled as if it were speech")


def test_every_fit_reports_its_length_and_its_budget_to_the_millisecond():
    """The track is written in milliseconds and the gaps are a second or two
    wide. A duration rounded to the nearest tenth is a 50ms error inside a 1.35s
    window, and rounded to the nearest second it is half a second, which is the
    difference between fitting and landing on a line. The budget is reported for
    the same reason: it is what the caller is told it had to work with."""
    class Precise:
        def duration(self, text):
            return 1.23456

    gap = 2.345          # a gap whose budget does not land on a round number
    f = fit_measured("A man crosses.", gap, Precise())
    assert abs(f.seconds - 1.23456) <= 0.0005, f.seconds
    assert abs(f.budget - budget_for(gap)) <= 0.0005, f.budget

    # Every other path that reports a budget, including the ones that failed.
    paths = [
        fit_generated(lambda n: "A man crosses.", gap, Precise()),
        fit_measured("A man in a grey coat crosses the empty street in snow.",
                     gap, FakeSynth()),
        fit_generated(lambda n: "", gap, FakeSynth()),
    ]
    for got in paths:
        assert abs(got.budget - budget_for(gap)) <= 0.0005, got

    # And the length on every path that reports one, not only the first. Three
    # of the four round their own number and only this one was ever read, so a
    # cue could be reported a half second shorter than it is.
    assert abs(paths[0].seconds - 1.23456) <= 0.0005, paths[0]
    plain = fit("A man crosses.", 6.0)
    assert abs(plain.seconds - speech_seconds(plain.text)) <= 0.0005, plain
    trimmed = fit("Snow fills the courtyard, thick and steady, "
                  "burying the parked cars.", 5.0)
    assert abs(trimmed.seconds - speech_seconds(trimmed.text)) <= 0.0005, trimmed

    estimated = fit("A man in a grey coat crosses the empty street in snow.", gap)
    assert abs(estimated.budget
               - (budget_for(gap) - ESTIMATE_ERROR_S)) <= 0.0005, estimated
    print(f"PASS a fit reports {f.seconds}s of {f.budget}s, not round numbers")


def test_a_description_that_exactly_fills_its_budget_is_accepted():
    """Every one of these comparisons could be strict and nothing would notice.
    A cue that fills its budget precisely is the normal case, not an edge one,
    and rejecting it silently discards good descriptions."""
    class Exact:
        """Says everything takes exactly the budget it was given."""

        def __init__(self, seconds):
            self.seconds = seconds

        def duration(self, text):
            return self.seconds

    exact = Exact(budget_for(4.0))
    assert fit_measured("A man crosses.", 4.0, exact).fits

    # The generated path must accept it on the first ask. Rejecting it and
    # asking again costs a vision call for a description it already had.
    asks = []
    got = fit_generated(lambda n: asks.append(n) or "A man crosses.", 4.0, exact)
    assert got.fits, got
    assert len(asks) == 1, f"a description that already fitted was re-asked: {asks}"

    # And the same boundary on the estimate-only path, where the budget is the
    # headroom less the estimator's own error.
    text = "A man crosses the empty street."
    gap = (speech_seconds(text) + ESTIMATE_ERROR_S) / HEADROOM
    assert speech_seconds(text) == budget_for(gap) - ESTIMATE_ERROR_S, "fixture"
    assert fit(text, gap).fits, (
        "a description that exactly filled its budget was refused")

    # The same again after a trim, which is a separate comparison.
    whole = "Snow fills the courtyard, thick and steady, burying the parked cars."
    cut = "Snow fills the courtyard, thick and steady."
    gap = (speech_seconds(cut) + ESTIMATE_ERROR_S) / HEADROOM
    assert speech_seconds(cut) == budget_for(gap) - ESTIMATE_ERROR_S, "fixture"
    assert fit(whole, gap).text == cut, fit(whole, gap)
    print("PASS a description that exactly fills its budget is scheduled")


def test_a_failed_fit_reports_no_time_at_all():
    """A fit with no text that still claims a duration is a cue that does not
    exist occupying a piece of the gap."""
    s = FakeSynth()
    long_ = "A man in a grey coat crosses the empty street as snow falls."
    for f in (fit_measured(long_, 1.5, s),
              fit_generated(lambda n: "", 6.0, s),
              fit(long_, 1.5)):
        assert not f.fits and f.text == "", f
        assert f.seconds == 0.0, f
    print("PASS a fit that failed reports no text and no seconds")


def test_a_budget_is_never_negative_and_never_bigger_than_its_gap():
    """A negative budget makes every comparison against it go the wrong way, and
    the gaps at the very start and end of a film round to nothing."""
    for gap in (0.0, 0.2, 0.5, 1.0):
        got = fit("A man crosses.", gap).budget
        assert got >= 0.0, gap
        # And the floor is a floor, not a free allowance: a budget larger than
        # the gap it came from would schedule speech straight over the next line.
        assert got <= budget_for(gap), f"a {gap}s gap was given a {got}s budget"
    print("PASS a gap too small to hold anything gets no budget, not a free one")


# --- the dangling rule, which is what keeps a cut sentence honest ------------

# The list is the guard, so a word quietly leaving it is a description quietly
# allowed to end there. Written out rather than iterated from the module,
# because a test that reads the list under test agrees with it by construction.
DANGLES = ("a", "an", "the", "and", "or", "but", "as", "of", "in", "on", "at",
           "to", "for", "with", "from", "into", "over", "under", "by", "his",
           "her", "its", "their", "this", "that", "these", "those", "is",
           "was", "are", "were", "then", "while", "when", "who", "which",
           "very", "more", "two", "three")


def test_every_word_on_the_dangling_list_still_stops_a_cut():
    """Each one is a word a description must never end on. "A man in a grey coat
    crosses the." is inside budget and leaves the listener waiting for a noun
    that never arrives."""
    assert set(DANGLES) == DANGLING, (
        "the list under test and the list in the module have drifted apart: "
        f"{set(DANGLES) ^ DANGLING}")
    s = FakeSynth()
    for word in DANGLES:
        text = f"A man crosses the street {word}, and the snow falls."
        f = fit_measured(text, 2.4, s)
        assert f.text == "", f"a description was allowed to end on {word!r}: {f}"
    print(f"PASS all {len(DANGLES)} dangling words still stop a cut")


def test_the_dangling_check_reads_the_last_word_and_is_not_fooled_by_punctuation():
    """It has to look at the end of the sentence, not the start, and a model
    leaves brackets and quotes lying around, so "the." is still "the"."""
    from aloud.budget import _ends_cleanly
    assert _ends_cleanly(["a", "door"]) is True
    assert _ends_cleanly(["door", "the"]) is False, "it read the wrong end"
    assert _ends_cleanly(["the."]) is False, "punctuation hid a dangling word"
    assert _ends_cleanly(["(the)"]) is False
    assert _ends_cleanly([]) is False, "an empty sentence ended cleanly"
    assert _ends_cleanly(["..."]) is False, "punctuation alone ended cleanly"
    print("PASS the dangling check reads the last word through its punctuation")


def test_a_description_of_nothing_but_punctuation_is_never_scheduled():
    """Trimming can arrive at a fragment with no words left in it. Synthesising
    that gives a cue containing a breath, which spends the gap and says
    nothing."""
    s = FakeSynth()
    f = fit_measured(", he leaves the room and closes the door behind him.",
                     1.6, s)
    assert f.text == "", f"a punctuation fragment was scheduled: {f.text!r}"
    print("PASS a fragment with no words in it is dropped")


def test_a_cooperative_describer_ends_up_with_a_description():
    """The generated path has to converge. The retry is scaled by how far over
    the last attempt went, so a writer that honours the target gets a
    description scheduled inside the gap. Scale it the wrong way and the loop
    runs out of rounds and the gap goes silent; collapse it to the floor and a
    four second gap gets two words."""
    s = FakeSynth()
    asks = []

    def describe(target):
        asks.append(target)
        return " ".join(["word"] * target)

    f = fit_generated(describe, 4.0, s)
    assert f.fits and f.text, f"a describer doing as it was told got nothing: {asks}"
    assert s.duration(f.text) <= f.budget, f
    assert len(f.text.split()) >= 5, (
        f"a {f.budget:.1f}s budget was filled with {len(f.text.split())} words")
    print(f"PASS the ask converged {asks} and filled the gap")


def test_a_describer_that_ignores_the_budget_is_truncated_rather_than_dropped():
    """Truncation is the guard underneath the generated path. By the time it
    runs something has already gone wrong, but a sentence with a clause boundary
    in it can still be saved, and dropping it loses a description that would
    have fitted."""
    s = FakeSynth()
    text = "Snow fills the courtyard, thick and steady, burying the parked cars."
    f = fit_generated(lambda n: text, 3.0, s)
    assert f.fits and f.text == "Snow fills the courtyard.", f
    assert f.trimmed, "a truncated description reported itself untouched"
    print("PASS a writer that ignores the budget still gets truncated, not dropped")


# --- fitting by estimate, with no synthesiser to check against ---------------

def test_the_estimate_only_path_holds_its_own_error_back():
    """`fit` has nothing to measure against, and the estimator is optimistic by
    up to ESTIMATE_ERROR_S on the reference voice. Without that margin it
    reports fits=True for a cue that runs past the end of its gap and onto the
    next line, and reports it confidently, because nothing measured anything."""
    budget = fit("A man crosses.", 6.0).budget
    assert budget <= budget_for(6.0) - ESTIMATE_ERROR_S + 1e-9, (
        f"the estimate-only budget {budget} does not hold back the "
        f"{ESTIMATE_ERROR_S}s the estimator is known to be wrong by")
    # And a description that only fits by less than that margin is refused.
    text = "A man in a grey coat crosses."
    gap = (speech_seconds(text) + 0.05) / HEADROOM
    assert speech_seconds(text) <= budget_for(gap), "fixture is not marginal"
    assert not fit(text, gap).fits, "a cue inside the estimate alone was accepted"

    # The margin is a margin and not a ban. Widen it and nothing is unsafe, it
    # is simply that no ordinary description fits an ordinary gap any more and
    # the estimate-only path stops being a fallback and becomes silence.
    ordinary = "A man crosses the empty street."
    assert fit(ordinary, 4.0).fits, (
        f"{speech_seconds(ordinary):.2f}s of description was refused a 4s gap")
    print("PASS the estimate-only path refuses what it cannot promise")


def test_the_estimate_only_path_trims_the_same_way_the_measured_one_does():
    """Two truncation rules that disagree is how a rule rots. The measured path
    refuses to cut inside a phrase, so this one must too."""
    text = "Snow fills the courtyard, thick and steady, burying the parked cars."
    f = fit(text, 5.0)
    assert f.fits and f.trimmed and f.text.endswith("."), f
    assert f.text == "Snow fills the courtyard, thick and steady.", f.text
    assert speech_seconds(f.text) <= f.budget, f
    print("PASS the estimate-only path cuts at a clause:", repr(f.text))


def test_text_that_already_fits_is_returned_untouched():
    text = "A man crosses."
    f = fit(text, 12.0)
    assert f.fits and not f.trimmed and f.text == text, f
    print("PASS a description that already fits is left alone")


# --- speech detection --------------------------------------------------------

def voiced(seconds, sr=SR):
    """A voice shaped like one: energy in the speech band, opening and closing
    at a syllable rate. It scores 0.99 where a real voice scores 0.55, which is
    why the real fixtures exist as well."""
    t = np.arange(int(sr * seconds)) / sr
    sig = sum(np.sin(2 * np.pi * f * t) * a
              for f, a in [(220, .5), (600, .7), (1400, .5), (2600, .3)])
    return (sig * (0.4 + 0.3 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)


def steady(seconds, sr=SR):
    """The same energy with no syllable rhythm. This is the shape of the thing
    that broke the band-only detector: it looks like speech to the band measure
    and nothing is talking."""
    t = np.arange(int(sr * seconds)) / sr
    sig = sum(np.sin(2 * np.pi * f * t) * a
              for f, a in [(220, .5), (600, .7), (1400, .5), (2600, .3)])
    return (sig * 0.5).astype(np.float32)


def swelling(seconds, rate, sr=SR):
    """Speech band energy rising and falling at `rate` Hz. A score swells and a
    tremolo flutters; neither is a mouth opening and closing."""
    t = np.arange(int(sr * seconds)) / sr
    sig = sum(np.sin(2 * np.pi * f * t) * a
              for f, a in [(220, .5), (600, .7), (1400, .5), (2600, .3)])
    return (sig * (0.4 + 0.3 * np.sin(2 * np.pi * rate * t))).astype(np.float32)


def tone(hz, seconds, amp=0.5, sr=SR):
    t = np.arange(int(sr * seconds)) / sr
    return (amp * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def hush(seconds, sr=SR):
    return (np.random.default_rng(7).standard_normal(int(sr * seconds))
            * 0.0015).astype(np.float32)


def test_silence_is_not_speech_shaped_noise():
    """A frame with no energy is silence, not "0% speech". Dividing two numbers
    that are both nearly zero gives whatever the noise felt like that day."""
    sp = speechiness(np.zeros(SR, dtype=np.float32), SR)
    assert len(sp) == 50, len(sp)
    assert float(sp.max()) == 0.0, sp.max()
    print("PASS digital silence scores zero, not a ratio of two nothings")


def test_an_empty_track_has_no_frames_and_no_gaps():
    assert len(speechiness(np.zeros(0, dtype=np.float32), SR)) == 0
    assert len(modulation(np.zeros(0, dtype=np.float32), SR)) == 0
    assert find_gaps(np.zeros(0, dtype=np.float32), SR) == []
    print("PASS an empty track produces nothing rather than raising")


def test_the_speech_band_keeps_a_male_fundamental_and_drops_the_rumble():
    """SPEECH_LOW is 200Hz and not the telephone band's 300Hz, because most male
    voices have their fundamental between 85 and 255Hz and a detector starting
    at 300 scores them as non-speech. The floor still has to sit above the
    rumble that scores and room tone live in."""
    assert float(speechiness(tone(250, 1.0), SR).mean()) > 0.9, (
        "a 250Hz fundamental was thrown away")
    assert float(speechiness(tone(100, 1.0), SR).mean()) < 0.1, (
        "low rumble scored as speech")
    assert float(speechiness(tone(8000, 1.0), SR).mean()) < 0.1, (
        "energy above the band scored as speech")
    print("PASS the band keeps 250Hz, drops 100Hz rumble and 8kHz hiss")


def test_a_near_silent_frame_is_not_speech_however_speech_shaped_it_is():
    """The loudness gate. Scraps of energy in the right band are not someone
    talking, and without this every quiet passage reads as dialogue and the film
    gets no descriptions at all."""
    loud = float(speechiness(tone(1000, 1.0, amp=0.5), SR).mean())
    faint = float(speechiness(tone(1000, 1.0, amp=0.0004), SR).mean())
    assert loud > 0.9, loud
    assert faint == 0.0, faint
    print(f"PASS the same tone scores {loud:.2f} loud and {faint:.2f} faint")


def test_the_syllable_rhythm_separates_a_voice_from_a_steady_sound():
    """The measure that band energy cannot provide. Broadband and sustained
    sounds both spread energy across the speech band; only a mouth opens and
    closes a few times a second."""
    assert float(modulation(voiced(2.0), SR).mean()) > \
        float(modulation(steady(2.0), SR).mean()) + 0.5
    print("PASS a modulated voice scores far above a sustained tone")


def test_modulation_reports_one_value_per_frame_even_for_a_short_clip():
    """A clip shorter than the analysis window still has to line up with the
    speechiness array frame for frame, or the two conditions are combined
    against the wrong frames."""
    for seconds in (0.2, 0.6, 2.0):
        clip = voiced(seconds)
        assert len(modulation(clip, SR)) == len(speechiness(clip, SR)), seconds
    print("PASS modulation and speechiness agree on the frame count")


def test_the_measure_is_a_fraction_of_energy_and_not_of_amplitude():
    """The docstring says fraction of energy, and the 0.45 threshold was chosen
    against that. Measuring amplitude instead moves every score without moving
    the threshold, which is how a detector ends up calibrated against a number
    that no longer means what it did."""
    inside = tone(1000, 1.0, amp=0.5)
    outside = tone(6000, 1.0, amp=1.0)
    # A quarter of the energy is in the band, not a third of the amplitude.
    got = float(speechiness(inside + outside, SR).mean())
    assert abs(got - 0.2) < 0.05, f"expected about 0.2 of the energy, got {got}"
    print(f"PASS a mix with a fifth of its energy in the band scores {got:.2f}")


def test_the_top_of_the_speech_band_is_included_and_the_hiss_above_it_is_not():
    """3500Hz is the top edge, and an edge nothing pins is an edge that drifts.
    The band was widened from the telephone 3400 deliberately."""
    assert float(speechiness(tone(3500, 1.0), SR).mean()) > 0.5, (
        "the top of the band was excluded from it")
    assert float(speechiness(tone(3600, 1.0), SR).mean()) < 0.1
    print("PASS 3500Hz is inside the band and 3600Hz is not")


def test_a_clip_too_short_to_have_a_rhythm_scores_none():
    """A rhythm is not a property of a few frames. Scoring one over a tenth of a
    second flatters noise, and a fabricated rhythm on top of speech-shaped noise
    is a description landing on top of the rain."""
    for seconds in (0.10, 0.14):
        got = modulation(voiced(seconds), SR)
        assert float(got.max()) == 0.0, (seconds, got)
    assert float(modulation(np.zeros(SR, dtype=np.float32), SR).max()) == 0.0, (
        "silence was given a syllable rhythm")
    # A flat envelope is the other way to have no rhythm, and it is the one that
    # divides by nothing if the guard goes. A test tone holds its level exactly.
    flat = modulation(np.full(SR, 0.5, dtype=np.float32), SR)
    assert float(flat.max()) == 0.0 and float(flat.min()) == 0.0, flat
    print("PASS too few frames, silence and a flat level all score no rhythm")


def test_a_clip_shorter_than_the_window_is_still_scored_on_the_rhythm_band():
    """Below a second there is no sliding window and the whole clip is scored at
    once. That path still has to measure the syllable band and not the whole
    spectrum, or every short clip comes back as a perfect rhythm and reads as
    somebody talking."""
    got = float(modulation(tone(1000, 0.4), SR).mean())
    assert 0.0 <= got < 0.5, f"a sustained tone scored {got} on the rhythm"
    print(f"PASS a short sustained clip scores {got:.2f}, not a perfect rhythm")


# --- smoothing, which is where the safety property is won or lost ------------

def mask(*runs):
    """mask(30, 5, 10) is 30 frames on, 5 off, 10 on."""
    out, on = [], True
    for n in runs:
        out += [on] * n
        on = not on
    return np.array(out, dtype=bool)


def test_runs_finds_every_run_including_one_that_reaches_the_end():
    assert _runs(np.array([], dtype=bool)) == []
    assert _runs(np.zeros(5, dtype=bool)) == []
    assert _runs(np.ones(5, dtype=bool)) == [(0, 5)]
    assert _runs(mask(2, 1, 2)) == [(0, 2), (3, 5)]
    print("PASS runs are found at the start, the middle and the end")


def test_the_quiet_tail_of_a_line_is_reattached_before_anything_is_dropped():
    """The order is the whole point. The tail of a line fragments into short
    runs, and dropping short runs first deletes it, which leaked half a second
    of real dialogue into a gap. Closing first reattaches the tail to the line
    it belongs to, and then nothing about it is short any more."""
    out = _smooth(mask(40, 8, 6, 20), FRAME_MS, 0.25, 0.20)
    assert out[:54].all(), "the tail of the line was dropped"
    assert not out[54:].any(), "the closing ran past the end of the line"
    print("PASS a fragmented tail is joined to its line, not dropped")


def test_an_isolated_blip_of_detector_noise_does_not_destroy_a_gap():
    """A music bed misreads a small fraction of its frames as speech. That
    scatter does not shrink a gap, it splits it into runs too short to use and
    the gap disappears entirely."""
    out = _smooth(mask(0, 30, 5, 30), FRAME_MS, 0.25, 0.20)
    assert not out.any(), "a five frame blip survived and split the gap"
    print("PASS a blip shorter than any real utterance is removed")


def test_the_opening_window_keeps_a_run_exactly_as_long_as_itself():
    """OPEN_S is 0.20s, which is ten frames. Ten frames of speech is speech and
    nine is noise, and a boundary nothing pins is a boundary that moves."""
    kept = _smooth(mask(0, 30, 10, 30), FRAME_MS, 0.25, 0.20)
    dropped = _smooth(mask(0, 30, 9, 30), FRAME_MS, 0.25, 0.20)
    assert kept[30:40].all(), "a run exactly the length of the window was dropped"
    assert not dropped.any(), "a run shorter than the window survived"
    print("PASS the opening window keeps ten frames and drops nine")


def test_the_closing_window_joins_a_hole_shorter_than_itself_and_no_more():
    """CLOSE_S is 0.25s, twelve frames. Joining more than that starts swallowing
    real gaps between lines, which is where the description was going to go."""
    joined = _smooth(mask(20, 11, 20), FRAME_MS, 0.25, 0.20)
    left = _smooth(mask(20, 12, 20), FRAME_MS, 0.25, 0.20)
    assert joined.all(), "an eleven frame hole inside a line was not closed"
    assert not left[20:32].any(), "a hole the length of the window was swallowed"
    print("PASS holes shorter than the window are closed, longer ones are kept")


def test_a_quiet_opening_to_the_film_is_not_a_hole_between_two_lines():
    """Closing joins speech across a hole. There is no speech before the start
    of the file, so a quiet lead-in is not a hole and filling it would turn the
    first moments of a film into dialogue nobody spoke."""
    out = _smooth(mask(0, 6, 40), FRAME_MS, 0.25, 0.20)
    assert not out[:6].any(), "the quiet before the first line became speech"
    print("PASS a quiet lead-in stays quiet")


# --- gaps, end to end on synthetic audio -------------------------------------

def test_a_gap_stops_short_of_the_dialogue_at_both_ends():
    """The safety property. Dialogue does not stop cleanly on a frame boundary,
    and a description that begins the instant a line ends sounds like an
    interruption even when it technically is not, so the gap is trimmed at both
    ends before anyone is allowed to use it."""
    track = np.concatenate([voiced(2.0), hush(3.0), voiced(2.0)])
    gaps = find_gaps(track, SR)
    assert len(gaps) == 1, gaps
    g = gaps[0]
    assert g.start >= 2.10, f"the gap opened {2.0 - g.start:.2f}s into the line"
    assert g.end <= 4.90, f"the gap ran {g.end - 5.0:.2f}s into the next line"
    assert g.start < 2.5 and g.end > 4.5, f"the padding ate the gap: {g}"
    print(f"PASS the gap sits inside the silence with room at both ends: {g}")


def test_a_sustained_sound_is_a_gap_because_nothing_is_talking():
    """Both conditions, not either. Speech-shaped energy says the sound could be
    a voice; the syllable rhythm says something is actually talking. A sustained
    chord passes the first and fails the second, and with `or` in place of `and`
    the film plays through an entire score with no description in it."""
    track = np.concatenate([voiced(2.0), steady(3.0), voiced(2.0)])
    gaps = find_gaps(track, SR)
    assert len(gaps) == 1, f"a sustained sound was heard as dialogue: {gaps}"
    assert gaps[0].start >= 2.0 and gaps[0].end <= 5.0, gaps
    print("PASS a sustained speech-band sound reads as a gap:", gaps[0])


def test_a_slow_swell_and_a_fast_flutter_are_not_speech():
    """The rhythm has a top and a bottom, because syllables have a rate. A score
    swelling once a second passes the speech band and is not a voice, and
    neither is a tremolo at nine a second. Only the 2Hz to 8Hz band is a mouth
    opening and closing, and the detector has to say so at both ends or every
    sustained musical passage reads as dialogue and gets no description."""
    for rate in (1.0, 9.0):
        track = np.concatenate([voiced(2.0), swelling(3.0, rate), voiced(2.0)])
        gaps = find_gaps(track, SR)
        assert len(gaps) == 1, f"{rate}Hz was heard as dialogue: {gaps}"
        assert gaps[0].start >= 2.0 and gaps[0].end <= 5.0, (rate, gaps)
    print("PASS a 1Hz swell and a 9Hz flutter both read as gaps")


def test_a_gap_that_runs_to_the_end_of_the_film_is_still_a_gap():
    """Nothing closes the last run, so it has to be closed by hand. The credits
    are the longest gap in most films."""
    track = np.concatenate([voiced(2.0), hush(3.0)])
    gaps = find_gaps(track, SR)
    assert len(gaps) == 1, gaps
    assert gaps[0].end >= 4.5, gaps
    assert gaps[0].end <= len(track) / SR, "the gap ran past the end of the film"
    print("PASS the final gap is closed at the end of the track:", gaps[0])


def test_a_short_line_between_two_silences_is_not_swallowed():
    """The safety property, from the other side. Opening the mask drops runs too
    short to be speech, and if that window grows past the length of a real line
    the line itself is deleted: the two gaps around it join into one, and the
    description is scheduled straight over the dialogue."""
    track = np.concatenate([hush(2.5), voiced(0.8), hush(2.5)])
    gaps = find_gaps(track, SR)
    assert len(gaps) == 2, f"a 0.8s line was swallowed into one gap: {gaps}"
    assert gaps[0].end <= 2.5 and gaps[1].start >= 3.3, gaps
    print("PASS a short line keeps the gaps on either side of it apart")


def test_the_times_reported_are_the_times_in_the_file():
    """Frames are converted to seconds by one multiplication, and getting it
    slightly wrong scales the whole timeline rather than moving one gap. A
    tenth of a percent is four milliseconds here and three and a half seconds by
    the end of a feature, by which point every cue is sitting on a line."""
    track = np.concatenate([voiced(6.0), hush(3.0), voiced(2.0)])
    got = find_gaps(track, SR)
    assert len(got) == 1, got
    # The silence runs 6.0s to 9.0s and 0.15s is trimmed off each end.
    assert abs(got[0].start - 6.15) <= 0.002, got[0].start
    assert abs(got[0].end - 8.85) <= 0.002, got[0].end
    print("PASS the reported times match the file to the millisecond:", got[0])


def test_a_gap_too_short_to_carry_a_description_is_not_reported():
    """Reporting it only sends the describer off to write something that can
    never be scheduled."""
    short = np.concatenate([voiced(2.0), hush(1.0), voiced(2.0)])
    assert find_gaps(short, SR) == []
    long = np.concatenate([voiced(2.0), hush(2.2), voiced(2.0)])
    assert len(find_gaps(long, SR)) == 1
    print("PASS a one second gap is dropped and a two second one is kept")


def test_a_gap_exactly_at_the_minimum_is_kept():
    """`>= min_gap`. The comparison could be strict and nothing would notice,
    and a gap of exactly the minimum is the case the constant was measured
    against."""
    track = np.concatenate([voiced(2.0), hush(3.0), voiced(2.0)])
    got = find_gaps(track, SR)[0]
    at = find_gaps(track, SR, min_gap=got.duration)
    assert len(at) == 1, f"a gap of exactly {got.duration}s was dropped"
    above = find_gaps(track, SR, min_gap=got.duration + 0.01)
    assert above == [], "a gap shorter than the minimum was kept"
    print(f"PASS a gap of exactly the minimum ({got.duration}s) is kept")


def test_a_gap_reports_its_own_length():
    assert Gap(2.0, 5.5).duration == 3.5
    assert "2.00" in repr(Gap(2.0, 5.5))
    print("PASS a gap knows how long it is")


def test_a_quietly_mixed_line_is_still_dialogue():
    """Every fixture above is at full scale and no film is. Nothing in the
    detector may depend on how loud the mix is, and the place that can is the
    syllable measure, which divides one energy sum by another and guards the
    division against zero. Move that guard anywhere off zero and a normally
    mixed film reads as one continuous silence, which puts a description over
    every line in it. At full scale the numbers are large enough that the guard
    never fires, so the fixtures above cannot see it."""
    for amp in (1.0, 0.2, 0.05):
        track = np.concatenate([voiced(2.0) * amp, hush(3.0), voiced(2.0) * amp])
        gaps = find_gaps(track, SR)
        assert len(gaps) == 1, f"at {amp:.2f} of full scale the film is {gaps}"
        assert gaps[0].start >= 2.10, (amp, gaps)
        assert gaps[0].end <= 4.90, (amp, gaps)
    print("PASS a line at a twentieth of full scale is still dialogue")


def test_a_fast_talker_is_inside_the_syllable_band():
    """The band has a top edge and the tests only ask about 4Hz in the middle of
    it and 9Hz outside it, so the edge itself can move a whole hertz unnoticed.
    Narrowing it to 7Hz keeps both of those answers and loses anyone speaking
    quickly: at 7.5 syllables a second the line stops counting as speech, the
    gaps either side of it join into one, and a description plays over the whole
    sentence."""
    track = np.concatenate([hush(2.0), swelling(2.0, 7.5), hush(2.0)])
    gaps = find_gaps(track, SR)
    assert len(gaps) == 2, f"a 7.5Hz speaker was heard as silence: {gaps}"
    assert gaps[0].end <= 2.0 and gaps[1].start >= 4.0, gaps
    print("PASS a voice at 7.5 syllables a second is still speech")


def test_the_smoothing_the_film_gets_is_the_smoothing_that_was_measured():
    """Every smoothing test above hands `_smooth` its two windows explicitly, so
    CLOSE_S and OPEN_S, the values a film actually gets, are never exercised.
    Either could be zeroed with the whole file still green, and each loses one
    of the two properties they were measured for: the quiet tail of a line stays
    part of that line, and a single misread frame inside a bed does not split a
    usable gap into two unusable ones."""
    # A line with a dropout in it and a 0.16s tail, which is too short to
    # survive on its own merits. Closing reattaches the tail to the line before
    # anything is eligible to be dropped, so the gap opens after 1.52s.
    tail = np.concatenate([voiced(1.2), hush(0.16), voiced(0.16),
                           hush(3.0), voiced(1.0)])
    got = find_gaps(tail, SR)
    assert len(got) == 1, got
    assert got[0].start >= 1.5, (
        f"the gap opened at {got[0].start:.2f}s, on top of a line that runs to "
        "1.52s")

    # A bed with one 0.12s misread in the middle of it. Opening removes it.
    # Without that the gap arrives as two of 1.2s, both under the minimum, and
    # the viewer is told nothing at all across three seconds of silence.
    blip = np.concatenate([voiced(1.5), hush(1.5), voiced(0.12),
                           hush(1.5), voiced(1.5)])
    got = find_gaps(blip, SR)
    assert len(got) == 1, f"a 0.12s misread split the gap in two: {got}"
    assert got[0].duration >= MIN_GAP_S, got
    print("PASS the close and open windows a film gets both do their job")


# --- reading the film's audio ------------------------------------------------

def write_wav(path, samples, sr=SR, channels=1):
    with wave.open(path, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(samples.astype("<i2").tobytes())
    return path


def temp_path(name):
    """Per-process. A fixed path in the temp directory makes the suite race
    against a second copy of itself, which is exactly what a mutation tester
    runs."""
    return os.path.join(tempfile.gettempdir(), f"aloud_logic_{os.getpid()}_{name}")


def test_audio_arrives_normalised_to_plus_or_minus_one():
    """BAND_RMS_FLOOR is an absolute threshold, and an absolute threshold only
    means anything if the scale is fixed. If the loader stops normalising, the
    loudness gate silently becomes a different gate on every file."""
    path = write_wav(temp_path("half.wav"),
                     np.full(SR, 16384, dtype=np.int16))
    try:
        audio, sr = load_audio(path)
        assert sr == SR, sr
        assert audio.dtype == np.float32, audio.dtype
        assert abs(float(audio.max()) - 0.5) < 0.01, float(audio.max())
        assert len(audio) == SR, len(audio)
    finally:
        os.remove(path)
    print("PASS a wav is read as float32 normalised to plus or minus one")


def test_audio_in_the_wrong_shape_is_converted_rather_than_misread():
    """The film arrives as whatever it arrives as, and the failure mode here is
    not an exception. Reading a stereo file as mono reads two channels as twice
    as many samples, which stretches the whole film: every gap the detector
    finds is then at the wrong time, and a description scheduled against the
    wrong clock lands on a line of dialogue.
    """
    if not shutil.which("ffmpeg"):
        print("SKIP no ffmpeg")
        return
    cases = {
        # stereo at the right rate, which is the one that reads as plausible
        # nonsense rather than failing
        "stereo.wav": (np.repeat(np.full(SR, 8000, dtype=np.int16), 2), SR, 2),
        "highrate.wav": (np.full(44100, 8000, dtype=np.int16), 44100, 1),
    }
    for name, (frames, rate, channels) in cases.items():
        path = write_wav(temp_path(name), frames, sr=rate, channels=channels)
        try:
            audio, sr = load_audio(path)
            assert sr == SR, (name, sr)
            assert audio.ndim == 1, (name, audio.shape)
            assert abs(len(audio) - SR) < SR * 0.05, (
                f"{name}: one second came back as {len(audio) / SR:.2f}s")
        finally:
            os.remove(path)
    print("PASS stereo and 44.1kHz files are converted, not read as they lie")


def test_audio_that_is_not_sixteen_bit_is_not_read_as_if_it_were():
    """An 8 bit file read two bytes at a time is noise of half the length, and
    noise has no speech in it, so the whole film reads as one long gap."""
    if not shutil.which("ffmpeg"):
        print("SKIP no ffmpeg")
        return
    path = temp_path("eightbit.wav")
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(1)
        w.setframerate(SR)
        w.writeframes(np.full(SR, 192, dtype=np.uint8).tobytes())
    try:
        audio, sr = load_audio(path)
        assert sr == SR
        assert abs(len(audio) - SR) < SR * 0.05, len(audio) / SR
        assert float(np.abs(audio).max()) <= 1.0, float(np.abs(audio).max())
    finally:
        os.remove(path)
    print("PASS an 8 bit file goes through the converter rather than being misread")


def test_audio_the_converter_cannot_read_is_an_error_not_an_empty_film():
    """ffmpeg failing has to raise. Returning whatever it managed to write gives
    an empty track, an empty track has no speech in it, and a film with no
    speech in it is one enormous gap that the describer will happily fill over
    every line in the picture."""
    if not shutil.which("ffmpeg"):
        print("SKIP no ffmpeg")
        return
    path = temp_path("notaudio.mp4")
    with open(path, "w") as f:
        f.write("this is not a film")
    try:
        try:
            load_audio(path)
            raise AssertionError("a file with no audio in it loaded cleanly")
        except AssertionError:
            raise
        except Exception:
            pass
    finally:
        os.remove(path)
    print("PASS a file the converter cannot read raises rather than going quiet")


# --- the synthesiser contract ------------------------------------------------

class _NoTools:
    """The path with no `say` and no ffmpeg on it."""

    @staticmethod
    def which(_name):
        return None


def without_a_synthesiser(fn):
    """No `say`, no ffmpeg, and no Kokoro model where the voice would look for
    one. Hiding only the binaries passed on a Mac and failed on a Linux box
    with the neural voice installed, which then reported, correctly, that it
    could speak."""
    real = synth_mod.shutil
    saved = {k: os.environ.get(k) for k in ("ALOUD_KOKORO_DIR", "ALOUD_TTS")}
    synth_mod.shutil = _NoTools
    os.environ["ALOUD_KOKORO_DIR"] = os.path.join(
        tempfile.gettempdir(), f"aloud-no-voice-{os.getpid()}")
    os.environ.pop("ALOUD_TTS", None)
    try:
        return fn()
    finally:
        synth_mod.shutil = real
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_an_empty_description_never_reaches_the_synthesiser():
    """Gaps with nothing worth saying are normal, and they must not cost a
    subprocess or raise on a machine with no voice installed."""
    def check():
        s = Synth()
        spoken = s.speak("   ")
        assert isinstance(spoken, Spoken)
        assert spoken.path is None and spoken.seconds == 0.0, spoken
        assert s.duration("") == 0.0
    without_a_synthesiser(check)
    print("PASS an empty description costs nothing and raises nothing")


def test_the_synthesiser_is_found_when_it_is_actually_there():
    """This probe decides whether the pipeline speaks at all, and it fails
    quietly in the worst possible way: the suites that need a voice print SKIP
    and pass, so a broken probe reads as a green run on a machine that could
    have spoken perfectly well."""
    have = bool(shutil.which("say") and shutil.which("ffmpeg"))
    if have:
        assert Synth().available, (
            "say and ffmpeg are both on this path and the probe did not find them")
        print("PASS the synthesiser on this machine is detected")
        return
    if synth_mod.kokoro_ready():
        assert Synth().available and Synth().backend == "kokoro", (
            "the Kokoro model is installed and the probe did not pick it")
        print("PASS the neural voice on this machine is detected")
        return
    print("SKIP no synthesiser on this machine")


def test_half_a_toolchain_is_not_a_synthesiser():
    """`say and ffmpeg`. With `or`, a machine carrying one of the two reports a
    working voice, the pipeline stops falling back to the estimator and starts
    scheduling real cues, and the failure arrives as a subprocess error partway
    through a film instead of as a missing voice before it starts."""
    class _OnlySay:
        @staticmethod
        def which(name):
            return "/usr/bin/say" if name == "say" else None

    class _OnlyFfmpeg:
        @staticmethod
        def which(name):
            return "/usr/bin/ffmpeg" if name == "ffmpeg" else None

    def check():
        real = synth_mod.shutil
        try:
            for half in (_OnlySay, _OnlyFfmpeg):
                synth_mod.shutil = half
                assert not Synth().available, f"{half.__name__} reported a voice"
        finally:
            synth_mod.shutil = real
    without_a_synthesiser(check)
    print("PASS a synthesiser needs both the voice and the converter")


def test_a_missing_synthesiser_is_an_error_and_not_a_zero():
    """A zero length would be taken as a cue that fits any gap. Better to fail
    where the voice is missing than to schedule silence and call it speech."""
    def check():
        s = Synth()
        assert not s.available
        try:
            s.speak("A man crosses the empty street.")
            raise AssertionError("a missing synthesiser returned a duration")
        except RuntimeError:
            pass
    without_a_synthesiser(check)
    print("PASS a missing synthesiser raises rather than reporting zero")


def test_an_adjective_list_is_not_a_clause():
    """The first full film produced "A large, dark." by cutting at a comma that
    separated two adjectives. A kept clause needs four words and no lone word
    between commas."""
    from aloud.budget import _shorten
    assert _shorten("A large, dark hall looms over the river.", 3) == ""
    assert _shorten("A large, dark, cavernous hall looms, its lights out.", 3) == ""
    assert _shorten("Snow fills the courtyard, drifting past the gate.", 3) == \
        "Snow fills the courtyard."
    assert _shorten("A man runs, then stops.", 2) == ""
    print("PASS a comma inside an adjective list is never a place to cut")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
