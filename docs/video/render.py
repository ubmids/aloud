"""Pre-renders for the demo video: everything that does not need a person.

    python3 docs/video/render.py cards OUT_DIR
        the title, section and end cards, lower third, caption and
        thumbnails, copied from design/assets/ (rendered there, in Signal)

    python3 docs/video/render.py viewer FILM OUT_DIR [--at 91 --length 39]
        the two clips for the viewer session: the scene with the film's own
        sound only, and the same scene as aloud plays it

    python3 docs/video/render.py lay RECORDING PLAN.json OUT.mp4
        put the app's sound under a Vega Virtual Device recording

Why `lay` exists. The Virtual Device records its screen through the emulator
console, and that recording has no audio track (docs/FRICTION_LOG.md,
entry 19). So the sound under each device recording is rebuilt from exactly
what the app plays: the film, dipped to the voice level's film volume while
a description speaks, and the description cues and menu clips that ship in
the package, at the voice level's volume, at the moments they played. The
plan file says what happened when:

    {"film": "path/to/film.mp4", "id": "tears-of-steel", "level": "normal",
     "speed": 0.816,
     "events": [
       {"t": 0.0, "film_at": 91.0, "until": 40.0, "narration": true},
       {"t": 2.1, "clip": "tv/assets/films/sintel/announce.m4a", "until": 5.0},
       {"t": 20.0, "repeat_at": 102.0},
       {"t": 0.0, "black_until": 9.5, "fade": 1.5}
     ]}

`speed` scales the recording's timestamps to real time (see record.py); all
other times are real seconds. `repeat_at` is a Menu press: the latest
description at or before that film time is said again.

`t` and `until` are seconds into the recording; `film_at` is the film's own
time at `t`. With `narration` true, every cue of the title's track that
starts inside that stretch is laid in at its own time, and the film dips
under it, which is what the player does. Nothing is invented: every sound
is the film or a file from the app package.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# tv/src/settings.ts, LEVELS: how loud the voice is, and how far the film
# dips while it speaks.
LEVELS = {"quiet": (0.65, 0.85), "normal": (0.85, 0.6), "loud": (1.0, 0.4)}



def _ffmpeg(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def _probe_duration(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True, check=True).stdout
    return float(out.strip())


def track(id: str) -> list[dict]:
    with open(os.path.join(ROOT, "tv", "src", "data", "films", f"{id}.json")) as f:
        cues = json.load(f)["cues"]
    d = os.path.join(ROOT, "tv", "assets", "films", id, "cues")
    return [{**c, "path": os.path.join(d, os.path.basename(c["audio"]))}
            for c in cues]


def sound(plan: dict, length: float, out_wav: str) -> str:
    """The app's audio for a recording `length` seconds long."""
    voice, dip = LEVELS[plan.get("level", "normal")]
    film = plan.get("film")
    cues = track(plan["id"]) if plan.get("id") else []
    inputs, parts, labels = [], [], []
    placed = []                       # (rec_t, path, gain, cut_at or None)
    duck = []                         # (rec_t0, rec_t1) where the film dips

    for e in plan["events"]:
        if "clip" in e:
            # A clip the next key press cut off (the app stops the voice on
            # every move) carries "until".
            placed.append((e["t"], e["clip"], e.get("gain", voice),
                           e.get("until")))
        if "film_at" in e:
            t0, until, at = e["t"], e.get("until", length), e["film_at"]
            n = len(parts)
            inputs += ["-ss", f"{at:.3f}", "-t", f"{until - t0:.3f}", "-i", film]
            parts.append((n, t0))
            if e.get("narration"):
                for c in cues:
                    if at <= c["start"] < at + (until - t0):
                        rt = t0 + c["start"] - at
                        placed.append((rt, c["path"], voice, None))
                        duck.append((rt, rt + c["end"] - c["start"]))
        if "repeat_at" in e:
            # Menu: the film is paused and the latest description is said
            # again, whether or not narration is on.
            past = [c for c in cues if c["start"] <= e["repeat_at"]]
            if past:
                placed.append((e["t"], past[-1]["path"], voice, None))

    filters = []
    for n, t0 in parts:
        ms = int(t0 * 1000)
        vol = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in duck) or "0"
        filters.append(
            f"[{n}:a]aresample=48000,adelay={ms}|{ms},"
            f"volume='if({vol},{dip},1)':eval=frame[f{n}]")
        labels.append(f"[f{n}]")
    k = len(parts)
    for i, (t, path, gain, cut) in enumerate(placed):
        inputs += (["-t", f"{cut - t:.3f}"] if cut else []) + ["-i", path]
        ms = int(t * 1000)
        filters.append(f"[{k + i}:a]aresample=48000,aformat=channel_layouts=stereo,"
                       f"volume={gain},adelay={ms}|{ms}[c{i}]")
        labels.append(f"[c{i}]")
    inputs += ["-f", "lavfi", "-t", f"{length:.3f}", "-i",
               "anullsrc=r=48000:cl=stereo"]
    labels.append(f"[{k + len(placed)}:a]")
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:"
                   f"duration=longest,atrim=0:{length:.3f}[out]")
    _ffmpeg(*inputs, "-filter_complex", ";".join(filters), "-map", "[out]",
            "-ac", "2", "-ar", "48000", out_wav)
    return out_wav


def lay(recording: str, plan_path: str, out: str) -> str:
    with open(plan_path) as f:
        plan = json.load(f)
    # "speed": the console's recorder clock runs slow under a moving picture
    # (record.py measures it); its timestamps are scaled back to real time.
    speed = float(plan.get("speed", 1.0))
    length = _probe_duration(recording) * speed
    with tempfile.TemporaryDirectory() as tmp:
        wav = sound(plan, length, os.path.join(tmp, "sound.wav"))
        vf = f"setpts=PTS*{speed:.5f},fps=30,scale=1920:1080,format=yuv420p"
        for e in plan["events"]:
            if "black_until" in e:
                vf += (f",fade=t=in:st={e['black_until']:.3f}:"
                       f"d={e.get('fade', 1.5):.3f}")
        _ffmpeg("-i", recording, "-i", wav, "-map", "0:v", "-map", "1:a",
                "-vf", vf, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                "-c:a", "aac", "-b:a", "192k", "-shortest", out)
    return out


def viewer(film: str, out_dir: str, at: float, length: float) -> list[str]:
    """Sound-only clips for the viewer session: a black picture, so whoever
    plays them on a laptop is not tempted to look."""
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for name, narration in (("tos-without.mp4", False), ("tos-with.mp4", True)):
        plan = {"film": film, "id": "tears-of-steel", "level": "normal",
                "events": [{"t": 0.0, "film_at": at, "until": length,
                            "narration": narration}]}
        with tempfile.TemporaryDirectory() as tmp:
            wav = sound(plan, length, os.path.join(tmp, "s.wav"))
            out = os.path.join(out_dir, name)
            _ffmpeg("-f", "lavfi", "-t", f"{length:.3f}", "-i",
                    "color=c=black:s=1280x720:r=30", "-i", wav, "-map", "0:v",
                    "-map", "1:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", out)
            made.append(out)
    return made


# --- cards ------------------------------------------------------------------

def cards(out_dir: str) -> list[str]:
    """The video cards are designed in design/assets/src/cards.html (Signal,
    design/DESIGN.md) and rendered there; this copies them beside the
    other assets so the edit has one folder."""
    import shutil
    src = os.path.join(ROOT, "design", "assets")
    os.makedirs(out_dir, exist_ok=True)
    made = []
    for name in sorted(os.listdir(src)):
        if name.endswith(".png"):
            made.append(shutil.copy(os.path.join(src, name), out_dir))
    return made


def main(argv=None):
    ap = argparse.ArgumentParser(prog="render.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("cards")
    c.add_argument("out_dir")
    v = sub.add_parser("viewer")
    v.add_argument("film")
    v.add_argument("out_dir")
    v.add_argument("--at", type=float, default=91.0)
    v.add_argument("--length", type=float, default=39.0)
    la = sub.add_parser("lay")
    la.add_argument("recording")
    la.add_argument("plan")
    la.add_argument("out")
    a = ap.parse_args(argv)
    if a.cmd == "cards":
        for p in cards(a.out_dir):
            print(p)
    elif a.cmd == "viewer":
        for p in viewer(a.film, a.out_dir, a.at, a.length):
            print(p)
    else:
        print(lay(a.recording, a.plan, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
