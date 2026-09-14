"""aloud <film> [--out DIR]

Describes a film and writes the track next to the audio you can listen to.
"""
import argparse
import os
import sys

from .pipeline import describe_film, mix


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aloud")
    ap.add_argument("video")
    ap.add_argument("--out", default="out")
    ap.add_argument("--no-mix", action="store_true")
    a = ap.parse_args(argv)

    os.makedirs(a.out, exist_ok=True)
    r = describe_film(a.video, out_dir=a.out)

    print(f"{len(r.gaps)} gap(s) in the dialogue, {len(r.shots)} shot change(s)")
    for c in r.track.cues:
        print(f"  {c.start:7.2f} - {c.end:6.2f}  {c.text}")
    for gap, why in r.skipped:
        print(f"  {gap.start:7.2f} - {gap.end:6.2f}  (nothing said: {why})")

    vtt = os.path.join(a.out, "description.vtt")
    js = os.path.join(a.out, "description.json")
    r.track.write(vtt_path=vtt, json_path=js, gaps=r.gaps)
    print(f"\nwrote {vtt}\nwrote {js}")

    if not a.no_mix and r.track.cues:
        mixed = mix(a.video, r, os.path.join(a.out, "described.mp4"))
        print(f"wrote {mixed}  <- play this one with your eyes shut")
    return 0


if __name__ == "__main__":
    sys.exit(main())
