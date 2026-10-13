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
         # A describer reads a 768 pixel frame as well as a 4K one, and on a
         # CPU the image is most of the cost of each description.
         "-frames:v", "1", "-vf", "scale='min(768,iw)':-2", "-q:v", "3",
         out_path],
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
    plans, last_said = [], 0.0
    shots = with_opening(shots, settle)
    for gap in gaps:
        plan = plan_one(gap, shots, last_said, lookahead=lookahead, settle=settle)
        plans.append(plan)
        if plan.worth_describing:
            last_said = gap.end
    return plans


def with_opening(shots, settle: float = 0.25):
    """The opening shot is never a cut, so nothing marks it and the first gap
    would go undescribed: the listener gets no idea where the film has put
    them. Treat the start as a change, since going from nothing to an image is
    the largest change there is."""
    shots = list(shots)
    if not any(s.at <= settle for s in shots):
        shots.insert(0, Shot(0.0, 1.0))
    return shots


def plan_one(gap, shots, last_said: float, *, lookahead: float = 0.0,
             settle: float = 0.25) -> Plan:
    """Whether one gap is worth a description, given when something was last
    actually said.

    `last_said` has to be what was SAID, not what was planned. Planning a whole
    film up front assumed every planned gap would be spoken, so when one was
    skipped (a black frame, a refused sentence, nothing fitting) every gap
    after it believed the listener had just been told about the picture. The
    Sintel trailer came out with no descriptions at all that way: its first
    gap is black, and the seven after it all reported "nothing has changed
    since the last cue". The pipeline now plans one gap at a time.
    """
    window_end = gap.start + lookahead
    new = [s for s in shots if last_said <= s.at <= window_end]
    if not new:
        return Plan(gap, None, "nothing has changed since the last cue")
    # The most RECENT change, not the biggest one. Ranking by score picked
    # the opening shot to describe a gap two cuts later, because a hard cut
    # from black outscores everything after it. That describes an image the
    # viewer moved past long ago, which is worse than saying nothing: it is
    # confidently wrong about what is on screen.
    #
    # Score decides WHETHER a change is worth words. Time decides WHICH
    # frame gets described. Conflating the two was the bug.
    chosen = max(new, key=lambda s: s.at)
    return Plan(gap, round(chosen.at + settle, 3),
                f"{len(new)} shot change(s) since the last cue")


def split_long_gaps(gaps, shots, *, longest: float = 8.0,
                    piece: float = 4.0, hard_cut: float = 0.25):
    """Cut long gaps at hard cuts, so an action sequence gets more than one cue.

    One gap, one description was right for a trailer and wrong for a film. The
    longest gap in *Tears of Steel* is forty seconds of battle with no dialogue
    and a dozen hard cuts, and it got a single sentence about the first shot:
    the listener then sat through thirty-five seconds of explosions with no idea
    who was winning. Professional describers talk most in exactly these
    stretches, because the picture is carrying the whole story.

    So a gap longer than `longest` is divided at its hard cuts (a change score
    of at least `hard_cut`, so a muzzle flash does not count) into pieces of
    at least `piece` seconds, each beginning on its cut. Every piece lies inside
    the original gap, so nothing here can move a cue onto dialogue, and the
    planner still decides piece by piece whether anything changed enough to be
    worth saying. Gaps with no hard cut in them stay whole: a long static shot
    needs describing once.
    """
    out = []
    for gap in gaps:
        if gap.duration <= longest:
            out.append(gap)
            continue
        cuts = sorted(s.at for s in shots
                      if s.score >= hard_cut
                      and gap.start + piece <= s.at <= gap.end - piece)
        start = gap.start
        for c in cuts:
            if c - start >= piece:
                out.append(type(gap)(round(start, 3), round(c, 3)))
                start = c
        out.append(type(gap)(round(start, 3), gap.end))
    return out


def next_cut_after(shots, t: float) -> float | None:
    """When the shot on screen at `t` ends, if it does."""
    later = [s.at for s in shots if s.at > t]
    return min(later) if later else None


# Mean luma, 0..255, below which a frame is treated as black. Films open on
# black, fade through it, and cut to it for effect, and a describer handed one
# says so: the first cue of the first full-length run was "Screen is completely
# black." That is true, it costs the opening gap, and it is the one thing a
# blind viewer already knows.
DARK_LUMA = 18.0


def brightness(path: str) -> float:
    """Mean luma of an image, read through ffmpeg so nothing new is needed."""
    _require_ffmpeg()
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf", "scale=64:-2,format=gray",
         "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    return (sum(raw) / len(raw)) if raw else 0.0


def first_lit_frame(video: str, start: float, end: float, out_dir: str,
                    step: float = 0.5) -> tuple[float, str] | None:
    """The first moment in [start, end) that is not black, and its frame."""
    t = start
    while t < end:
        path = frame_at(video, t, os.path.join(out_dir, f"{t:.3f}.jpg"))
        if brightness(path) >= DARK_LUMA:
            return t, path
        t += step
    return None


# Mean absolute difference between two 64x36 greyscale thumbnails, 0..255,
# above which the picture counts as changed. Measured on the Sintel trailer and
# Tears of Steel: the same shot a few seconds apart scores 3 to 25, a different
# scene 50 to 110.
LOOKS_DIFFERENT = 40.0


def _thumb(video: str, t: float):
    import numpy as np
    raw = subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{max(0.0, t):.3f}", "-i", video,
         "-frames:v", "1", "-vf", "scale=64:36,format=gray", "-f", "rawvideo",
         "-"], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).astype(np.float32)


def picture_change(video: str, a: float, b: float) -> float:
    """How different the picture at `b` is from the picture at `a`."""
    x, y = _thumb(video, a), _thumb(video, b)
    n = min(len(x), len(y))
    return float(abs(x[:n] - y[:n]).mean()) if n else 0.0


def changed_since(video: str, described_at: float | None, gap,
                  settle: float = 0.25) -> Plan | None:
    """A second test for change, for what cut detection cannot see.

    Cut detection scores each frame against the one before it, so a slow
    dissolve, a fade through black or a long camera move changes the whole
    picture without any single frame scoring as a cut. The Sintel trailer is
    almost all dissolves, and after its first half nothing in it registered as
    a change: four gaps over entirely new scenes were left silent. So when no
    cut is found, the picture in the gap is compared with the last picture that
    was actually described, and a big enough difference counts.
    """
    if described_at is None:
        return None
    at = round(gap.start + settle, 3)
    if picture_change(video, described_at, at) >= LOOKS_DIFFERENT:
        return Plan(gap, at, "the picture has changed since the last cue")
    return None
