"""What to describe, when to stay quiet, and never talking over dialogue."""
import atexit
import os
import subprocess
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.gaps import Gap
from aloud.scenes import Shot, detect_shots, plan_descriptions
from aloud.track import Cue, Track, schedule

# Per-process, not a fixed path. A shared /tmp file makes the suite
# non-hermetic: run two copies at once, as any mutation tester or parallel CI
# does, and they race on the same file. Mutiny caught this by giving a different
# verdict for the same mutant on different runs, which is exactly the symptom.
FILM = os.path.join(tempfile.gettempdir(),
                    f"aloud_test_film_{os.getpid()}.mp4")


def make_film():
    """Three solid colours, two hard cuts at 3s and 6s."""
    if os.path.exists(FILM):
        return True
    if not shutil.which("ffmpeg"):
        return False
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y",
         "-f", "lavfi", "-i", "color=c=navy:s=320x180:d=3",
         "-f", "lavfi", "-i", "color=c=darkgreen:s=320x180:d=3",
         "-f", "lavfi", "-i", "color=c=maroon:s=320x180:d=3",
         "-filter_complex", "[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]",
         "-map", "[v]", "-pix_fmt", "yuv420p", FILM], check=True)
    atexit.register(lambda: os.path.exists(FILM) and os.remove(FILM))
    return True


def test_scene_scores_are_read_not_assumed():
    """Regression. The first version stored the threshold in the score field, so
    every shot carried the same number and ranking by 'biggest change' ranked by
    nothing. Two equally hard cuts genuinely score 0.37 and 0.17."""
    if not make_film():
        print("SKIP no ffmpeg")
        return
    shots = detect_shots(FILM)
    assert len(shots) == 2, shots
    assert len({s.score for s in shots}) == 2, f"scores are identical: {shots}"
    print("PASS real scene scores read:", shots)


def test_a_conservative_threshold_drops_real_cuts():
    """Regression. The default was 0.25, and a genuine cut scores 0.17."""
    if not make_film():
        print("SKIP no ffmpeg")
        return
    assert len(detect_shots(FILM, threshold=0.25)) == 1
    assert len(detect_shots(FILM, threshold=0.10)) == 2
    print("PASS a 0.25 threshold silently loses a cut, 0.10 keeps it")


def test_the_opening_shot_is_always_described():
    """The start of a film is not a cut, so nothing marks it, and the listener
    would be given no idea where they are."""
    gaps = [Gap(1.0, 2.8)]
    plans = plan_descriptions(gaps, [Shot(3.0, 0.37)])
    assert plans[0].worth_describing, plans[0].reason
    assert plans[0].describe_at < 1.0
    print("PASS the opening shot is described:", plans[0].describe_at)


def test_nothing_new_means_nothing_said():
    """The rule that keeps this from being exhausting. A gap with no visual
    change behind it gets no cue, because repeating the same room every few
    seconds is worse than silence."""
    shots = [Shot(0.0, 1.0), Shot(3.0, 0.37)]
    gaps = [Gap(1.0, 2.8), Gap(4.0, 5.8), Gap(7.0, 8.5)]
    plans = plan_descriptions(gaps, shots)
    assert [p.worth_describing for p in plans] == [True, True, False], \
        [(p.gap, p.reason) for p in plans]
    assert "nothing has changed" in plans[2].reason
    print("PASS a gap with nothing new behind it gets no cue")


def test_the_chosen_frame_is_past_the_cut():
    """The first frame of a shot is often a blur, a whip pan or half a dissolve.
    Describing it produces confident nonsense."""
    plans = plan_descriptions([Gap(4.0, 5.8)], [Shot(0.0, 1.0), Shot(3.0, 0.37)])
    assert plans[0].describe_at > 3.0, plans[0].describe_at
    print("PASS the described frame sits past the cut:", plans[0].describe_at)


def test_a_track_that_would_talk_over_dialogue_is_refused():
    """The safety property of the whole product. A cue landing on a line removes
    information the listener already had, so this refuses rather than warns."""
    gaps = [Gap(2.15, 4.85), Gap(6.65, 8.85)]
    good = Track(cues=[Cue(*schedule(gaps[0], 1.98), "A man crosses the street.")])
    assert good.validate(gaps) == []

    bad = Track(cues=[Cue(5.0, 6.0, "this lands on a line of dialogue")])
    problems = bad.validate(gaps)
    assert problems and "over dialogue" in problems[0]

    # Clear it first. This assertion is about what THIS run wrote, and a stale
    # file from a previous run makes the test fail for the wrong reason. It
    # actually happened: a Mutiny mutant that removed the refusal wrote the file
    # for real, the mutant was correctly killed, and the evidence sat on disk
    # failing this test afterwards.
    out = os.path.join(tempfile.gettempdir(),
                       f"aloud_should_not_exist_{os.getpid()}.vtt")
    if os.path.exists(out):
        os.remove(out)
    try:
        bad.write(vtt_path=out, gaps=gaps)
        raise AssertionError("an unsafe track was written")
    except ValueError:
        pass
    assert not os.path.exists(out), "an unsafe track reached disk"
    print("PASS an unsafe track is refused, not warned about")


# --- found by Mutiny, not by thinking harder --------------------------------
# Each of these corresponds to a mutation the suite above waved through. The
# first group is the worst: the safety check that no cue lands on dialogue had
# its boundary and its tolerance direction both unprotected, so the one rule
# this system must never break was resting on untested code.

def test_the_safety_check_holds_exactly_at_the_gap_edges():
    """`s - tolerance <= c.start and c.end <= e + tolerance`.

    Both comparisons could be made strict and nothing noticed. A cue that fills
    its gap precisely is the normal case, not an edge one, and rejecting it
    would silently discard good descriptions.
    """
    gaps = [Gap(2.0, 5.0)]
    exact = Track(cues=[Cue(2.0, 5.0, "fills the gap precisely")])
    assert exact.validate(gaps) == [], exact.validate(gaps)

    # And a hair outside on either side must still be caught.
    for bad in (Cue(1.90, 4.0, "starts too early"),
                Cue(3.0, 5.10, "ends too late")):
        problems = Track(cues=[bad]).validate(gaps)
        assert problems and "over dialogue" in problems[0], (bad.text, problems)
    print("PASS a cue exactly filling its gap is accepted, either side rejected")


def test_the_tolerance_widens_the_window_it_does_not_narrow_it():
    """`e + tolerance` could have been `e - tolerance` unnoticed. Tolerance
    exists to forgive floating point, so it must forgive in both directions."""
    gaps = [Gap(2.0, 5.0)]
    within = Track(cues=[Cue(1.995, 5.005, "a rounding error outside")])
    assert within.validate(gaps) == [], within.validate(gaps)
    print("PASS the tolerance forgives rounding at both ends")


def test_adjacent_cues_are_allowed_but_overlapping_ones_are_not():
    """`b.start < a.end - tolerance`. Two cues that merely touch are fine; one
    that starts before the previous finishes is two voices at once."""
    gaps = [Gap(0.0, 12.0)]
    touching = Track(cues=[Cue(1.0, 4.0, "one"), Cue(4.0, 7.0, "two")])
    assert touching.validate(gaps) == [], touching.validate(gaps)

    overlapping = Track(cues=[Cue(1.0, 4.0, "one"), Cue(3.5, 7.0, "two")])
    assert any("overlap" in p for p in overlapping.validate(gaps))
    print("PASS touching cues are fine, overlapping ones are caught")


def test_the_vtt_timestamps_are_actually_correct():
    """Nothing verified the timestamp format at all, so the whole track could
    have been written with wrong times and every test would still pass. Hours
    matter: a film longer than an hour is the normal case."""
    t = Track(cues=[
        Cue(0.0, 1.5, "at the very start"),
        Cue(61.25, 63.0, "just past a minute"),
        Cue(3725.5, 3727.0, "just past an hour"),
    ])
    vtt = t.to_vtt()
    assert vtt.startswith("WEBVTT"), vtt[:20]
    assert "00:00:00.000 --> 00:00:01.500" in vtt, vtt
    assert "00:01:01.250 --> 00:01:03.000" in vtt, vtt
    assert "00:62:05.500" not in vtt, "minutes overflowed instead of rolling into hours"
    assert "01:02:05.500 --> 01:02:07.000" in vtt, vtt
    print("PASS VTT timestamps are correct through hours, minutes and millis")


def test_a_cue_knows_how_long_it_is():
    """`self.end - self.start` could have been `+`, or dropped entirely."""
    assert Cue(2.0, 5.5, "x").duration == 3.5
    assert Cue(0.0, 0.25, "x").duration == 0.25
    print("PASS a cue reports its own duration")


def test_a_shot_exactly_on_the_threshold_counts():
    """`score >= threshold`. The comparison could have been strict and the
    boundary was never pinned, which matters because the threshold is the number
    that decides whether a real cut is seen at all."""
    if not make_film():
        print("SKIP no ffmpeg")
        return
    shots = detect_shots(FILM, threshold=0.10)
    lowest = min(s.score for s in shots)
    # Setting the threshold to exactly the lowest score must still include it.
    at_boundary = detect_shots(FILM, threshold=lowest)
    assert len(at_boundary) == len(shots), (
        f"a cut scoring exactly {lowest} was dropped at threshold {lowest}")
    just_above = detect_shots(FILM, threshold=lowest + 0.01)
    assert len(just_above) < len(shots)
    print(f"PASS a cut scoring exactly the threshold ({lowest}) is kept")


def test_every_alignment_places_the_cue_inside_the_gap():
    """`schedule()` has three alignments and only one had a test, so two thirds
    of the placement logic could have been arbitrary. Every one of them must
    keep the cue inside the gap, since that is the safety property."""
    gap = Gap(10.0, 16.0)
    spoken = 2.5
    for align in ("start", "centre", "end"):
        a, b = schedule(gap, spoken, align=align)
        assert gap.start <= a and b <= gap.end, (align, a, b)
        assert abs((b - a) - spoken) < 0.001, (align, b - a)
    # And each puts it where it says.
    assert schedule(gap, spoken, "start")[0] == gap.start
    assert abs(schedule(gap, spoken, "end")[1] - gap.end) < 1e-9
    centre = schedule(gap, spoken, "centre")
    assert centre[0] > gap.start and centre[1] < gap.end
    print("PASS start, centre and end all place the cue inside the gap")


def test_a_cue_longer_than_its_gap_is_still_clamped():
    """Nothing should be able to make schedule() return a window that leaves
    the gap, even when asked to place something that cannot fit."""
    gap = Gap(10.0, 12.0)
    for align in ("start", "centre", "end"):
        a, b = schedule(gap, 5.0, align=align)
        assert a >= gap.start - 1e-9, (align, a)
        assert b <= gap.end + 1e-9, (align, b)
    print("PASS an oversized cue is clamped rather than allowed to overrun")


def test_the_track_serialises_everything_a_player_needs():
    """`to_dict` had no test, so the JSON the app consumes was unverified."""
    gaps = [Gap(2.0, 6.0)]
    t = Track(source="film.mp4",
              cues=[Cue(2.0, 4.5, "A man crosses.", audio="/tmp/a.wav",
                        gap=(2.0, 6.0))])
    d = t.to_dict()
    assert d["source"] == "film.mp4"
    c = d["cues"][0]
    assert c["start"] == 2.0 and c["end"] == 4.5
    assert c["text"] == "A man crosses."
    assert c["audio"] == "/tmp/a.wav"
    assert c["gap"] == [2.0, 6.0]
    print("PASS the serialised track carries times, text, audio and its gap")


def test_overlapping_cues_are_caught():
    gaps = [Gap(2.0, 9.0)]
    t = Track(cues=[Cue(2.0, 5.0, "one"), Cue(4.5, 7.0, "two")])
    assert any("overlap" in p for p in t.validate(gaps))
    print("PASS cues overlapping each other are caught")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
