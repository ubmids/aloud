"""Deciding what to describe, and when to say nothing.

The obvious pipeline fills every gap it finds. That produces something
exhausting: a voice restating the same room every four seconds because there was
room to. Human describers do the opposite. They describe what *changed*, and
they are comfortable leaving a gap empty when nothing has.

So the unit here is not the gap, it is the visual change. Shot boundaries are
detected across the whole film, each gap is matched to the changes that happened
since the last thing said, and a gap with nothing new behind it gets no cue.
That rule does more for how the result feels than any amount of caption quality.
"""
import json
import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class Shot:
    at: float          # when the cut happens
    score: float       # how big a change ffmpeg thought it was, 0..1


@dataclass
class Plan:
    gap: object
    describe_at: float | None   # timestamp of the frame to describe
    reason: str

    @property
    def worth_describing(self) -> bool:
        return self.describe_at is not None


def _require_ffmpeg():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("ffmpeg and ffprobe are needed to read video")


def duration_of(video: str) -> float:
    _require_ffmpeg()
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "json", video], capture_output=True, check=True).stdout
    return float(json.loads(out)["format"]["duration"])


def detect_shots(video: str, threshold: float = 0.10) -> list[Shot]:
    """Shot boundaries with their real change scores.

    Two things here were wrong in the first version and both mattered.

    The scores are read out of ffmpeg rather than assumed. Selecting with
    `gt(scene,T)` tells you a cut happened but not how big it was, and the first
    version stored the threshold in the score field, so every shot carried an
    identical number and "describe the biggest change in this window" was
    ranking by nothing at all.

    The threshold is also lower than it looks like it should be. On a test film
    of three solid colours, two equally hard cuts scored 0.37 and 0.17, because
    the score reflects how far the pixels moved and not whether a cut occurred.
    A threshold that sounds conservative silently drops real cuts, and a missed
    cut means describing an image that is no longer on screen, which is worse
    than a redundant description. Spurious cuts are cheap: the change filter
    downstream drops most of them.
    """
    _require_ffmpeg()
    proc = subprocess.run(
        ["ffmpeg", "-v", "info", "-i", video,
         "-filter:v", "select='gte(scene,0)',metadata=print:file=-",
         "-f", "null", "-"],
        capture_output=True, text=True)

    shots, pending = [], None
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        line = line.strip()
        if "pts_time:" in line:
            try:
                pending = float(line.split("pts_time:")[1].split()[0])
            except (IndexError, ValueError):
                pending = None
        elif "lavfi.scene_score=" in line and pending is not None:
            try:
                score = float(line.split("=")[1])
            except (IndexError, ValueError):
                continue
            if score >= threshold:
                shots.append(Shot(round(pending, 3), round(score, 3)))
            pending = None
    return shots


def frame_at(video: str, t: float, out_path: str) -> str:
    """Pull a single frame for the describer to look at."""
    _require_ffmpeg()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, t):.3f}", "-i", video,
         "-frames:v", "1", "-q:v", "3", out_path],
        check=True, capture_output=True)
    return out_path


def plan_descriptions(gaps, shots, *, lookahead: float = 0.0,
                      settle: float = 0.25) -> list[Plan]:
    """Match each gap to the visual change it should be describing.

    A gap earns a description when at least one shot boundary falls between the
    last thing said and the moment this gap opens. Otherwise the picture has not
    changed since the listener was last told about it, and the honest thing is
    to stay quiet.

    `settle` nudges the chosen frame past the cut itself, because the first
    frame of a shot is often a whip pan, a blur, or half a dissolve, and
    describing it produces confident nonsense.
    """
    # The opening shot is never a cut, so nothing marks it and the first gap
    # would go undescribed: the listener gets no idea where the film has put
    # them. Treat the start as a change, since going from nothing to an image is
    # the largest change there is.
    shots = list(shots)
    if not any(s.at <= settle for s in shots):
        shots.insert(0, Shot(0.0, 1.0))

    plans, last_said = [], 0.0
    for gap in gaps:
        window_end = gap.start + lookahead
        new = [s for s in shots if last_said <= s.at <= window_end]
        if not new:
            plans.append(Plan(gap, None, "nothing has changed since the last cue"))
            continue
        # The most RECENT change, not the biggest one. Ranking by score picked
        # the opening shot to describe a gap two cuts later, because a hard cut
        # from black outscores everything after it. That describes an image the
        # viewer moved past long ago, which is worse than saying nothing: it is
        # confidently wrong about what is on screen.
        #
        # Score decides WHETHER a change is worth words. Time decides WHICH
        # frame gets described. Conflating the two was the bug.
        chosen = max(new, key=lambda s: s.at)
        plans.append(Plan(gap, round(chosen.at + settle, 3),
                          f"{len(new)} shot change(s) since the last cue"))
        last_said = gap.end
    return plans
