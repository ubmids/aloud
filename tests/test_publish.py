"""Putting a track on the shelf, and the things that must stop it getting there.

`publish` is the last step before a track ships inside an app, so it checks
the safety property once more and refuses rather than writes. It also has to
leave the app with exactly what the app reads: every cue's audio by name, the
spoken title, the poster, and a track file with its provenance.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.films import BY_ID, TITLES, announcement
from aloud.publish import publish
from aloud.synth import Spoken


def tone(path, seconds=0.6, sr=16000):
    t = np.arange(int(sr * seconds)) / sr
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((np.sin(2 * np.pi * 440 * t) * 8000).astype("<i2").tobytes())
    return path


class Voice:
    def speak(self, text, out_dir=None):
        os.makedirs(out_dir, exist_ok=True)
        return Spoken(text, tone(os.path.join(out_dir, "said.wav")), 0.6)


def setup(cues):
    d = tempfile.mkdtemp(prefix="aloud_pub_")
    out, app = os.path.join(d, "out"), os.path.join(d, "app")
    os.makedirs(out)
    film = os.path.join(d, "film.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    "color=c=teal:s=320x180:d=40", "-pix_fmt", "yuv420p", film],
                   check=True)
    for c in cues:
        c["audio"] = tone(os.path.join(out, f"{c['start']}.wav"))
    with open(os.path.join(out, "description.json"), "w") as f:
        json.dump({"source": film, "describer": "test-model (local)",
                   "voice": "test voice", "cues": cues}, f)
    return d, out, app


def test_a_published_title_has_everything_the_app_reads():
    if not shutil.which("ffmpeg"):
        print("SKIP no ffmpeg")
        return
    cues = [{"start": 1.0, "end": 2.0, "text": "A man crosses.", "gap": [1.0, 3.0]},
            {"start": 5.0, "end": 6.5, "text": "Snow falls.", "gap": [4.8, 7.0]}]
    d, out, app = setup(cues)
    try:
        data = publish(out, "sintel-trailer", app, synth=Voice())
        root = os.path.join(app, "assets", "films", "sintel-trailer")
        assert [c["audio"] for c in data["cues"]] == ["cue-001.m4a", "cue-002.m4a"]
        for c in data["cues"]:
            assert os.path.getsize(os.path.join(root, "cues", c["audio"])) > 0
        assert os.path.getsize(os.path.join(root, "announce.m4a")) > 0
        assert os.path.getsize(os.path.join(app, "src", "assets", "posters",
                                            "sintel-trailer.jpg")) > 0
        with open(os.path.join(app, "src", "data", "films", "sintel-trailer.json")) as f:
            on_disk = json.load(f)
        assert on_disk["describer"] == "test-model (local)"
        assert on_disk["announcement"] == announcement(BY_ID["sintel-trailer"], 2)
        assert on_disk["source"] == "film.mp4", on_disk["source"]
        assert "Blender Foundation" in on_disk["credit"]
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("PASS a published title carries its cues, spoken title, poster and provenance")


def test_a_track_that_would_land_on_dialogue_is_not_published():
    if not shutil.which("ffmpeg"):
        print("SKIP no ffmpeg")
        return
    for bad in ([{"start": 1.0, "end": 3.5, "text": "Too long.", "gap": [1.0, 3.0]}],
                [{"start": 1.0, "end": 2.0, "text": "One.", "gap": [1.0, 3.0]},
                 {"start": 1.5, "end": 2.5, "text": "Two.", "gap": [1.0, 3.0]}],
                [{"start": 1.0, "end": 2.0, "text": "No gap.", "gap": None}]):
        d, out, app = setup(bad)
        try:
            publish(out, "sintel-trailer", app, synth=Voice())
            raise AssertionError(f"published an unsafe track: {bad}")
        except ValueError:
            assert not os.path.exists(os.path.join(app, "src", "data"))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    print("PASS an unsafe track is refused before anything reaches the app")


def test_every_title_names_an_official_source_and_its_credit():
    for t in TITLES:
        assert t.url.startswith("https://download.blender.org/"), t.url
        assert "Blender Foundation" in t.credit, t.id
        assert t.year and t.minutes and t.genre, t.id
    assert announcement(BY_ID["sintel-trailer"], 7) == \
        "Sintel: the trailer. Trailer, 2010, 1 minute. 7 descriptions."
    # Every film with people in it carries its cast, so the describer can
    # call them what the film calls them.
    for id in ("sintel", "big-buck-bunny", "sintel-trailer"):
        assert BY_ID[id].cast, id
    assert "Sintel" in BY_ID["sintel"].cast and "Scales" in BY_ID["sintel"].cast
    print("PASS every title comes from the Blender mirror with its credit")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
