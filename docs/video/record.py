"""Record the app shots for the demo video on the Vega Virtual Device.

    python3 docs/video/record.py FILM OUT_DIR [--only cold,shelf,player]

FILM is the original `tears_of_steel_720p.mov` (only for working out which
moment of the film is on screen). The Virtual Device must be running with
the current build installed:

    vega virtual-device start --no-gui
    vega run-app tv/build/aarch64-release/aloud_aarch64.vpkg

Each shot relaunches the app, drives it with remote keys through
`inputd-cli` (FRICTION_LOG entry 20), records the screen through the
emulator console (entry 19), and then lays the app's own sound under the
picture with `render.py`, because the console records picture only.

Two things are measured from the recording rather than assumed:

  * **Which moment of the film is on screen.** Frames of the recording are
    matched against the film (normalised correlation of small greyscale
    thumbnails), so the sound laid under it is the sound of those frames.
  * **The recorder's clock.** Under a moving picture the console's recorder
    writes timestamps that run slow (about 0.8 of real time on an M2 Pro),
    while the device plays the film in real time (its log shows 0.249 s of
    film per 0.254 s of wall clock). The recording is retimed by the
    measured film rate, so the film plays at its own speed in the asset.

Nothing is invented: every sound is the film or a file from the app package,
placed where the app played it.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
import render  # noqa: E402

APP = "com.subomiolagoke.aloud.main"
ENV = dict(os.environ, PATH=os.path.expanduser("~/vega/bin") + ":" + os.environ["PATH"])
TOKEN_FILE = os.path.expanduser("~/.emulator_console_auth_token")
W, H = 96, 40

# Where the film sits on screen, at 1920x1080, in each layout. The film is
# 2.4:1, so full screen letterboxes it; the panel pillarboxes it inside the
# stage. A crop a little inside the picture keeps the bars out of the match.
CROP_FULL = "crop=1840:740:40:170"
CROP_PANEL = "crop=1176:467:116:162"


# --- the device -------------------------------------------------------------

def console(cmd: str) -> str:
    with open(TOKEN_FILE) as f:
        token = f.read().strip()
    s = socket.create_connection(("127.0.0.1", 5554))
    s.settimeout(3)
    s.sendall(f"auth {token}\r\n".encode())
    time.sleep(0.3)
    s.sendall(f"{cmd}\r\n".encode())
    time.sleep(0.4)
    try:
        out = s.recv(65536).decode(errors="ignore")
    except OSError:
        out = ""
    s.sendall(b"quit\r\n")
    s.close()
    return out


def vega(*args):
    return subprocess.run(["vega", *args], env=ENV, capture_output=True, text=True)


def key(k: str):
    vega("device", "run-cmd", "-c", f"inputd-cli button_press {k}")


def relaunch(settle: float = 6.0):
    vega("device", "terminate-app", "--appName", APP)
    time.sleep(1.5)
    vega("device", "launch-app", "--appName", APP)
    time.sleep(settle)


class Recording:
    """A screen recording with a log of key presses, in recorder seconds."""

    def __init__(self, path: str):
        self.path, self.keys = path, []
        if os.path.exists(path):
            os.remove(path)

    def __enter__(self):
        t = time.time()
        console(f"screenrecord start --fps 30 {self.path}")
        self.t0 = (t + time.time()) / 2
        return self

    def press(self, k: str):
        key(k)
        self.keys.append((round(time.time() - self.t0, 2), k))

    def __exit__(self, *exc):
        console("screenrecord stop")
        time.sleep(2)


# --- reading the film off the screen ----------------------------------------

def _thumbs(path: str, vf: str, fps: float, ss: float = 0, dur: float | None = None):
    args = ["ffmpeg", "-v", "error", "-ss", f"{ss}"]
    if dur:
        args += ["-t", f"{dur}"]
    if path.endswith(".png"):
        args += ["-loop", "1", "-t", "1.5"]   # a still, as a short clip
    raw = subprocess.run(args + ["-i", path, "-vf",
                                 f"{vf + ',' if vf else ''}fps={fps},scale={W}:{H},format=gray",
                                 "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, H, W).astype(float)
    a = a - a.mean(axis=(1, 2), keepdims=True)
    return a / (a.std(axis=(1, 2), keepdims=True) + 1e-6)


def film_times(rec: str, film: str, crop: str, lo: float, hi: float,
               step: float = 0.5, min_corr: float = 0.9):
    """[(recording seconds, film seconds or None)] every `step` seconds."""
    f = _thumbs(film, "", 25, lo, hi - lo)
    r = _thumbs(rec, crop, 1 / step)
    out = []
    for i, x in enumerate(r):
        c = (f * x).mean(axis=(1, 2))
        j = int(np.argmax(c))
        out.append((i * step, lo + j / 25 if c[j] >= min_corr else None))
    return out


def fit(samples):
    """Film time = a + b * recording time, by least squares over the samples
    that matched, dropping any more than half a second off the line."""
    pts = np.array([(t, s) for t, s in samples if s is not None])
    for _ in range(3):
        b, a = np.polyfit(pts[:, 0], pts[:, 1], 1)
        keep = np.abs(pts[:, 1] - (a + b * pts[:, 0])) < 0.5
        if keep.all():
            break
        pts = pts[keep]
    return float(a), float(b), len(pts)


_WHOLE: dict = {}


def where_now(film: str, crop: str) -> float | None:
    d = os.path.join(OUT, "_where")
    os.makedirs(d, exist_ok=True)
    for f in os.listdir(d):
        os.remove(os.path.join(d, f))
    console(f"screenrecord screenshot {d}")
    time.sleep(1.0)        # the console returns before the PNG is fully written
    shots = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".png")]
    if not shots:
        return None
    x = _thumbs(shots[0], crop, 2)[0]
    if film not in _WHOLE:                  # the whole film, once, at 5 fps
        _WHOLE[film] = _thumbs(film, "", 5)
    f = _WHOLE[film]
    c = (f * x).mean(axis=(1, 2))
    j = int(np.argmax(c))
    return j / 5 if c[j] > 0.85 else None


def seek_to(film: str, crop: str, target: float, early: float = 4.0):
    """Skip in tens of seconds until the film is just before `target`, then
    let it play up to it."""
    for _ in range(30):
        t = where_now(film, crop)
        if t is None:
            time.sleep(1)
            continue
        if t < target - 10 - early:
            key("KEY_FASTFORWARD")
        elif t > target - 1:
            key("KEY_REWIND")
        else:
            time.sleep(max(0.0, target - t - early))
            return
        time.sleep(0.6)
    raise RuntimeError("could not reach the target time")


# --- the shots ---------------------------------------------------------------

def shot_shelf(film, out):
    """The shelf: every title and every setting read out as focus arrives."""
    relaunch()
    rec = os.path.join(out, "rec-shelf.webm")
    with Recording(rec) as r:
        time.sleep(2)
        for k, wait in (("KEY_RIGHT", 3.6), ("KEY_RIGHT", 3.6), ("KEY_LEFT", 2.6),
                        ("KEY_LEFT", 4.6), ("KEY_DOWN", 4.0), ("KEY_RIGHT", 4.0),
                        ("KEY_RIGHT", 4.5)):
            r.press(k)
            time.sleep(wait)
    a = "tv/assets"
    said = [f"{a}/films/sintel/announce.m4a", f"{a}/films/big-buck-bunny/announce.m4a",
            f"{a}/films/sintel/announce.m4a", f"{a}/films/tears-of-steel/announce.m4a",
            f"{a}/ui/narration-on.m4a", f"{a}/ui/level-normal.m4a",
            f"{a}/ui/density-full.m4a"]
    times = focus_changes(rec, len(said)) or [t for t, _ in r.keys]
    events = [{"t": t, "clip": c, **({"until": times[i + 1]} if i + 1 < len(times) else {})}
              for i, (t, c) in enumerate(zip(times, said))]
    plan = {"level": "normal", "events": events}
    return lay(rec, plan, os.path.join(out, "02-shelf.mp4"), "02-shelf")


def focus_changes(rec: str, n: int):
    """The first `n` moments the screen changed, after the first second."""
    x = _thumbs(rec, "", 10)
    d = np.abs(np.diff(x, axis=0)).mean(axis=(1, 2))
    found, last = [], -9
    for i in np.argsort(-d):
        if (i + 1) / 10 > 1.0 and all(abs(i - j) > 8 for j in found):
            found.append(i)
        if len(found) == n:
            break
    return sorted(round((i + 1) / 10, 1) for i in found) if len(found) == n else None


def shot_cold(film, out, start=90.5, length=36.0, reveal_at=103.0):
    """The cold open: Tears of Steel from 1:30.5 in full screen, with
    narration on. The first description lands six seconds in (1:36.5); the
    picture is held black until the film reaches `reveal_at`, during the
    second, and fades up on the flying ship in the rifle scope."""
    relaunch()
    key("KEY_ENTER")                        # play Tears of Steel
    time.sleep(10)
    # The player's settings are a column (Signal layout): Picture is the
    # fourth, three presses down from Narration.
    for k in ("KEY_DOWN", "KEY_DOWN", "KEY_DOWN", "KEY_ENTER"):      # Picture: Full screen
        key(k)
        time.sleep(0.8)
    time.sleep(4)
    seek_to(film, CROP_FULL, start)
    rec = os.path.join(out, "rec-cold.webm")
    with Recording(rec):
        time.sleep(length)
    samples = film_times(rec, film, CROP_FULL, start - 15, start + length + 10)
    a, b, n = fit(samples)
    plan = {"film": film, "id": "tears-of-steel", "level": "normal", "speed": b,
            "fit": {"a": a, "b": b, "points": n},
            "events": [{"t": 0.0, "film_at": a, "until": length * b,
                        "narration": True},
                       {"t": 0.0, "black_until": reveal_at - a, "fade": 1.5}]}
    return lay(rec, plan, os.path.join(out, "01-cold-open.mp4"), "01-cold-open")


def shot_player(film, out, start=58.0):
    """The player with the voice panel: a description and the dip, then
    narration off, then Menu repeating the latest description."""
    relaunch()
    key("KEY_ENTER")
    time.sleep(10)
    seek_to(film, CROP_PANEL, start)
    rec = os.path.join(out, "rec-player.webm")
    with Recording(rec) as r:
        time.sleep(17)                      # 63.4 s and 69.9 s descriptions
        r.press("KEY_ENTER")                # Narration off
        time.sleep(6)
        r.press("KEY_MENU")                 # repeat the latest description
        time.sleep(9)
    samples = film_times(rec, film, CROP_PANEL, start - 15, start + 50)
    keys = {k: t for t, k in r.keys}
    t_off, t_menu = keys["KEY_ENTER"], keys["KEY_MENU"]
    before = [(t, s) for t, s in samples if t < t_menu - 0.5]
    after = [(t, s) for t, s in samples if t > t_menu + 4.5]
    a1, b, _ = fit(before)
    a2, b2, _ = fit(after)
    # Recorder seconds become real seconds by the film rate `b`.
    sp = b
    menu_at = t_menu * sp
    # The film stops at a1 + b*t_menu and starts again from the same frame;
    # the second line says when, in recorder seconds.
    paused_until = ((a1 + b * t_menu) - a2) / b2 * sp
    plan = {"film": film, "id": "tears-of-steel", "level": "normal", "speed": sp,
            "events": [
                {"t": 0.0, "film_at": a1, "until": t_off * sp, "narration": True},
                {"t": t_off * sp, "clip": "tv/assets/ui/narration-off.m4a"},
                {"t": t_off * sp, "film_at": a1 + b * t_off, "until": menu_at,
                 "narration": False},
                {"t": menu_at, "repeat_at": a1 + b * t_menu},
                {"t": paused_until, "film_at": a1 + b * t_menu,
                 "until": max(samples[-1][0] * sp, paused_until + 1),
                 "narration": False}]}
    return lay(rec, plan, os.path.join(out, "03-player.mp4"), "03-player")


def lay(rec, plan, out_mp4, name):
    os.makedirs(os.path.join(HERE, "plans"), exist_ok=True)
    plan_path = os.path.join(HERE, "plans", f"{name}.json")
    with open(plan_path, "w") as f:
        json.dump(plan, f, indent=1)
    return render.lay(rec, plan_path, out_mp4)


OUT = HERE


def main(argv=None):
    global OUT
    ap = argparse.ArgumentParser(prog="record.py")
    ap.add_argument("film")
    ap.add_argument("out_dir")
    ap.add_argument("--only", default="shelf,cold,player")
    a = ap.parse_args(argv)
    OUT = os.path.abspath(a.out_dir)
    os.makedirs(OUT, exist_ok=True)
    os.chdir(ROOT)
    shots = {"shelf": shot_shelf, "cold": shot_cold, "player": shot_player}
    for s in a.only.split(","):
        print(shots[s](os.path.abspath(a.film), OUT), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
