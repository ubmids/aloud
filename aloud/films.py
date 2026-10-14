"""The films on the shelf, where they come from, and how to get them.

    python3 -m aloud.films fetch [--only ID] [--app tv]    films into the app
    python3 -m aloud.films build [--only ID] [--app tv]    and describe them

`build` is the whole thing: download each film and its captions from the
mirror, run the pipeline with whichever describer the environment selects
(see docs/DESCRIBERS.md), and publish the track, the spoken cues and the
film into the app. Regenerating every title with a hosted model is that
command with a key set.

Every title is an open film from the Blender Foundation, fetched from the
Foundation's own mirror at download.blender.org and re-encoded for a
television app package. The full-length films are too large for a git
repository, so the repository carries their description tracks and spoken
cues, and this command puts the films beside them before a build. The trailer
is small enough to be committed, and is.

A track is only valid against the timeline it was built on. Re-encoding keeps
every timestamp (no trimming, no frame-rate change), so a track built on the
mirror's file plays correctly against the encode this writes.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from dataclasses import dataclass


@dataclass(frozen=True)
class Title:
    id: str
    title: str
    url: str
    # The file inside the download, when the mirror ships a zip.
    member: str | None = None
    # The title's own caption file. Its timing is used as a dialogue map;
    # the words are not.
    captions: str | None = None
    # The production stems, where the film publishes them, for evaluation.
    stems: tuple[str, str] | None = None
    credit: str = ""
    licence: str = "Creative Commons Attribution 3.0"
    genre: str = ""
    year: int = 0
    minutes: int = 0
    # A moment that makes a good poster, in seconds.
    poster_at: float = 0.0
    # Who is in it, as the film names them, with what a viewer sees of them,
    # so the describer can say "Sintel" rather than "the red-haired figure".
    cast: str = ""


# Sintel says her own name, and names the dragon. The old man never is.
SINTEL_CAST = ("Sintel: a young woman with short red hair, who carries a "
               "staff and later a spear. Scales: a small baby dragon. Any "
               "full-grown dragon is just 'a dragon'.")

TITLES = [
    Title(
        id="tears-of-steel",
        title="Tears of Steel",
        url="https://download.blender.org/demo/movies/ToS/tears_of_steel_720p.mov",
        captions="https://download.blender.org/demo/movies/ToS/subtitles/TOS-en.srt",
        stems=("https://download.blender.org/demo/movies/ToS/TOS_DVDSTEREOMIX.aif",
               "https://download.blender.org/demo/movies/ToS/"
               "TOS_MUSIC%2BFX_NO_DIALOGUE.aif"),
        credit="(CC) Blender Foundation | mango.blender.org",
        genre="Science fiction", year=2012, minutes=12, poster_at=250.0,
    ),
    Title(
        id="sintel",
        title="Sintel",
        url="https://download.blender.org/durian/movies/Sintel.2010.720p.mkv.zip",
        member="Sintel.2010.720p.mkv",
        # The English captions are inside the film itself, as its fourth
        # stream: `ffmpeg -i Sintel.2010.720p.mkv -map 0:3 sintel_en.srt`.
        captions="embedded:0:3",
        credit="(c) copyright Blender Foundation | durian.blender.org",
        genre="Fantasy", year=2010, minutes=15, poster_at=70.0,
        cast=SINTEL_CAST,
    ),
    Title(
        id="big-buck-bunny",
        title="Big Buck Bunny",
        url="https://download.blender.org/peach/bigbuckbunny_movies/"
            "big_buck_bunny_720p_h264.mov.zip",
        member="big_buck_bunny_720p_h264.mov",
        # No dialogue at all: the whole film is a gap, cut up by its shots.
        credit="(c) copyright 2008, Blender Foundation | www.bigbuckbunny.org",
        genre="Family comedy", year=2008, minutes=10, poster_at=75.0,
        # Only the title names anyone: the film has no dialogue, and its
        # three bullies are named in the credits alone. Naming them anyway
        # went wrong twice on the way here (the describer called the
        # chinchilla "Bunny", then swapped the two squirrels), so they are
        # described by what a viewer sees, as the brief asks for anyone the
        # film has not named.
        cast=("Bunny: a huge, fat, fluffy white rabbit, much bigger than "
              "everyone else; the only rabbit. Nobody else is named: "
              "describe the three small bullies by how they look (a flying "
              "squirrel, a red squirrel, a grey chinchilla)."),
    ),
    Title(
        id="sintel-trailer",
        title="Sintel: the trailer",
        url="https://download.blender.org/durian/trailer/sintel_trailer-720p.mp4",
        credit="(c) copyright Blender Foundation | durian.blender.org",
        genre="Trailer", year=2010, minutes=1, poster_at=30.0,
        cast=SINTEL_CAST,
    ),
]

BY_ID = {t.id: t for t in TITLES}


def announcement(t: Title, cues: int) -> str:
    """What the shelf says when this title takes focus. Written into the
    track file and read by the app, so the words on the tile's screen-reader
    label and the words in the spoken clip are the same words by construction."""
    plural = "" if t.minutes == 1 else "s"
    return (f"{t.title}. {t.genre}, {t.year}, {t.minutes} minute{plural}. "
            f"{cues} descriptions.")

# Small enough to bundle, sharp enough for a 1080p television at sofa distance.
# Main profile at level 3.1 is what the Vega media pipeline decodes in hardware.
ENCODE = ["-vf", "scale=854:-2", "-c:v", "libx264", "-profile:v", "main",
          "-level", "3.1", "-crf", "25", "-preset", "slow", "-pix_fmt", "yuv420p",
          "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-movflags", "+faststart"]


def download(url: str, dest: str) -> str:
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    tmp = dest + ".part"
    print(f"downloading {url}", file=sys.stderr)
    with urllib.request.urlopen(url) as r, open(tmp, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    os.replace(tmp, dest)
    return dest


def source(t: Title, cache: str) -> str:
    """The original film from the mirror, unzipped if it ships zipped."""
    got = download(t.url, os.path.join(cache, t.id, os.path.basename(t.url)))
    if t.member:
        out = os.path.join(cache, t.id, t.member)
        if not os.path.exists(out):
            with zipfile.ZipFile(got) as z:
                z.extract(t.member, os.path.join(cache, t.id))
        return out
    return got


def encode(src: str, dest: str) -> str:
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to encode the films")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, *ENCODE, tmp],
                   check=True)
    os.replace(tmp, dest)
    return dest


def captions_for(t: Title, cache: str, film: str) -> str | None:
    if not t.captions:
        return None
    if t.captions.startswith("embedded:"):
        out = os.path.join(cache, t.id, "captions.srt")
        if not os.path.exists(out):
            stream = t.captions.split(":", 1)[1]
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", film,
                            "-map", stream, out], check=True)
        return out
    return download(t.captions, os.path.join(cache, t.id,
                                             os.path.basename(t.captions)))


def build(t: Title, app: str, cache: str) -> dict:
    from .pipeline import describe_film
    from .publish import publish

    film = source(t, cache)
    captions = captions_for(t, cache, film)
    out = os.path.join(cache, t.id, "out")
    r = describe_film(film, out_dir=out, captions=captions, quiet=False,
                      cast=t.cast or None)
    r.track.write(vtt_path=os.path.join(out, "description.vtt"),
                  json_path=os.path.join(out, "description.json"), gaps=r.gaps)
    dest = app_film_path(app, t.id)
    return publish(out, t.id, app, film=None if os.path.exists(dest) else film)


def app_film_path(app: str, id: str) -> str:
    return os.path.join(app, "assets", "films", id, "film.mp4")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aloud.films")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fetch", help="download and encode the films into the app")
    f.add_argument("--only", choices=sorted(BY_ID))
    f.add_argument("--app", default="tv")
    f.add_argument("--cache", default=os.path.join(tempfile.gettempdir(),
                                                   "aloud-films"))
    b = sub.add_parser("build", help="fetch, describe and publish into the app")
    b.add_argument("--only", choices=sorted(BY_ID))
    b.add_argument("--app", default="tv")
    b.add_argument("--cache", default=os.path.join(tempfile.gettempdir(),
                                                   "aloud-films"))
    sub.add_parser("list")
    a = ap.parse_args(argv)

    if a.cmd == "list":
        for t in TITLES:
            print(f"{t.id:16s} {t.title:22s} {t.url}")
        return 0

    if a.cmd == "build":
        for t in TITLES:
            if a.only and t.id != a.only:
                continue
            d = build(t, a.app, a.cache)
            print(f"{t.id}: {len(d['cues'])} descriptions by {d['describer']}")
        return 0

    for t in TITLES:
        if a.only and t.id != a.only:
            continue
        dest = app_film_path(a.app, t.id)
        if os.path.exists(dest):
            print(f"{t.id}: already in place, {dest}")
            continue
        encode(source(t, a.cache), dest)
        print(f"{t.id}: {dest} ({os.path.getsize(dest) / 1e6:.1f}MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
