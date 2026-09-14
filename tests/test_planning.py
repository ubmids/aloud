"""What to describe, when to stay quiet, and never talking over dialogue."""
import os
import subprocess
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.gaps import Gap
from aloud.scenes import Shot, detect_shots, plan_descriptions
from aloud.track import Cue, Track, schedule

FILM = "/tmp/aloud_test_film.mp4"


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
    try:
        bad.write(vtt_path="/tmp/should_not_exist.vtt", gaps=gaps)
        raise AssertionError("an unsafe track was written")
    except ValueError:
        pass
    assert not os.path.exists("/tmp/should_not_exist.vtt")
    print("PASS an unsafe track is refused, not warned about")


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
