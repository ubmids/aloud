"""Put a described film on the shelf.

    python3 -m aloud.publish OUT_DIR --id tears-of-steel [--app tv] [--film FILE]

Takes what `python3 -m aloud` wrote and lays it out the way the app reads it:

    tv/src/data/films/<id>.json           the track, cue audio named by file
    tv/assets/films/<id>/cues/cue-NN.m4a  one spoken file per description
    tv/assets/films/<id>/announce.m4a     the title, read for the shelf
    tv/src/assets/posters/<id>.jpg        a still for the shelf
    tv/assets/films/<id>/film.mp4         only with --film

The track is validated again on the way in. A track that reached this point has
already passed the pipeline's own check, but this is the last step before it
ships inside an app, and the check is cheap.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

from .caption import unfit
from .films import BY_ID, announcement, encode
from .synth import Synth


def _m4a(src: str, dest: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ac", "1",
                    "-c:a", "aac", "-b:a", "64k", dest], check=True)


def publish(out_dir: str, id: str, app: str = "tv", film: str | None = None,
            synth=None) -> dict:
    title = BY_ID[id]
    with open(os.path.join(out_dir, "description.json")) as f:
        track = json.load(f)

    cues = track.get("cues", [])
    for a, b in zip(cues, cues[1:]):
        if b["start"] < a["end"]:
            raise ValueError(f"cues overlap at {b['start']}s; not publishing")
    for c in cues:
        g = c.get("gap")
        if not g or c["start"] < g[0] - 0.01 or c["end"] > g[1] + 0.01:
            raise ValueError(f"cue at {c['start']}s is outside its gap; not publishing")
        # The same sentence gate the pipeline applies, once more, so a track
        # written before the gate existed, or edited by hand, cannot carry a
        # sentence that stops before its noun or talks about the camera.
        why = unfit(c.get("text", ""))
        if why:
            raise ValueError(f"cue at {c['start']}s: {why} "
                             f"({c.get('text', '')!r}); not publishing")

    root = os.path.join(app, "assets", "films", id)
    cue_dir = os.path.join(root, "cues")
    shutil.rmtree(cue_dir, ignore_errors=True)
    os.makedirs(cue_dir)
    for i, c in enumerate(cues, 1):
        name = f"cue-{i:03d}.m4a"
        if c.get("audio"):
            _m4a(c["audio"], os.path.join(cue_dir, name))
            c["audio"] = name

    said = announcement(title, len(cues))
    synth = synth or Synth()
    spoken = synth.speak(said, out_dir=os.path.join(out_dir, "announce"))
    _m4a(spoken.path, os.path.join(root, "announce.m4a"))

    poster = os.path.join(app, "src", "assets", "posters", f"{id}.jpg")
    os.makedirs(os.path.dirname(poster), exist_ok=True)
    src = film or track.get("source")
    if src and os.path.exists(src):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{title.poster_at:.2f}",
                        "-i", src, "-frames:v", "1", "-vf", "scale=960:-2",
                        "-q:v", "4", poster], check=True)
    if film:
        encode(film, os.path.join(root, "film.mp4"))

    data = {
        "id": id,
        "title": title.title,
        "source": os.path.basename(track.get("source", "")),
        "describer": track.get("describer", ""),
        **({"revised_by": track["revised_by"]} if track.get("revised_by") else {}),
        "voice": track.get("voice", ""),
        "announcement": said,
        "credit": title.credit,
        "licence": title.licence,
        "cues": cues,
    }
    dest = os.path.join(app, "src", "data", "films", f"{id}.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    return data


def regate(app: str, id: str, synth=None, drop=(), respeak: bool = True) -> list:
    """Bring a track that is already on the shelf under the sentence gate.

    For a title that is not being re-described: each cue the gate refuses is
    taken off, with its audio, and the gap it sat in is left silent, which is
    what the pipeline would have done. The other cues keep their times and
    their files. The shelf announcement is re-spoken with the new count.
    Returns the cues removed; an empty list means nothing changed.

    `drop` is the start times of cues a reviewer has refused outright, for
    what no word list can catch: a model that describes a man in a film with
    no people in it. Matched to the hundredth of a second.

    `respeak=False` updates the announcement's words but leaves its audio,
    for a machine without the voice the shelf was made with; `announce`
    re-speaks it later, so the shelf never mixes two voices.
    """
    title = BY_ID[id]
    dest = os.path.join(app, "src", "data", "films", f"{id}.json")
    with open(dest) as f:
        data = json.load(f)
    keep, removed = [], []
    refused = {round(float(t), 2) for t in drop}
    for c in data["cues"]:
        out = unfit(c.get("text", "")) or round(c["start"], 2) in refused
        (removed if out else keep).append(c)
    if not removed:
        return []
    root = os.path.join(app, "assets", "films", id)
    for c in removed:
        if c.get("audio"):
            path = os.path.join(root, "cues", c["audio"])
            if os.path.exists(path):
                os.remove(path)
    data["cues"] = keep
    data["announcement"] = announcement(title, len(keep))
    with open(dest, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    if respeak:
        announce(app, id, synth=synth)
    return removed


def announce(app: str, id: str, synth=None) -> str:
    """Speak a shelf title's announcement again, from the words in its track
    file, so the spoken count always matches the cues that ship."""
    dest = os.path.join(app, "src", "data", "films", f"{id}.json")
    with open(dest) as f:
        said = json.load(f)["announcement"]
    synth = synth or Synth()
    work = tempfile.mkdtemp(prefix="aloud-announce-")
    spoken = synth.speak(said, out_dir=work)
    _m4a(spoken.path, os.path.join(app, "assets", "films", id, "announce.m4a"))
    return said


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aloud.publish")
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--id", required=True, choices=sorted(BY_ID))
    ap.add_argument("--app", default="tv")
    ap.add_argument("--film", help="also encode this film into the app")
    ap.add_argument("--regate", action="store_true",
                    help="apply the sentence gate to the track already in the app")
    ap.add_argument("--drop", type=float, action="append", default=[],
                    metavar="START", help="with --regate: also remove the cue "
                    "starting at START seconds, refused in review")
    ap.add_argument("--no-respeak", action="store_true",
                    help="with --regate: update the announcement's words only; "
                    "run --announce later with the shelf's voice")
    ap.add_argument("--announce", action="store_true",
                    help="re-speak the title's announcement from its track file")
    a = ap.parse_args(argv)
    if a.announce:
        print(f"{a.id}: {announce(a.app, a.id)}")
        return 0
    if a.regate:
        for c in regate(a.app, a.id, drop=a.drop, respeak=not a.no_respeak):
            why = unfit(c["text"]) or "refused in review"
            print(f"removed {c['start']}s: {why}: {c['text']}")
        return 0
    if not a.out_dir:
        ap.error("out_dir is required unless --regate")
    d = publish(a.out_dir, a.id, a.app, a.film)
    print(f"{a.id}: {len(d['cues'])} cues, described by {d['describer']}, "
          f"read by {d['voice']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
