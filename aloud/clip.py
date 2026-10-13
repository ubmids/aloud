"""The cold open for the video, cut from a described film.

    python3 -m aloud.clip FILM OUT_DIR --at 60 --length 16 --reveal 8 --out hero.mp4

The opening of the demo is a contrast a judge can feel: a few seconds of black
screen with the film's own sound, which is what a blind viewer gets, then the
same black screen with aloud describing it, then the picture coming up on the
moment that was described. This makes that clip from the pipeline's own
output (`described.mp4`, the film with its descriptions mixed in) so the voice
in the video is the voice in the app.

  without.mp4   black, the film's own audio, `length` seconds from `at`
  hero.mp4      black, the described mix, the picture fading in at `reveal`
"""
import argparse
import os
import subprocess
import sys


def cut(film: str, described: str, at: float, length: float, reveal: float,
        out_dir: str, name: str = "hero.mp4") -> tuple[str, str]:
    os.makedirs(out_dir, exist_ok=True)
    without = os.path.join(out_dir, "without.mp4")
    hero = os.path.join(out_dir, name)
    # Black over the film's own sound.
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-t", f"{length:.3f}",
         "-i", film, "-f", "lavfi", "-t", f"{length:.3f}",
         "-i", "color=c=black:s=1280x534:r=24",
         "-map", "1:v", "-map", "0:a", "-c:v", "libx264", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", without], check=True)
    # Black over the described mix, the picture fading up at `reveal`.
    fade = (f"[0:v]scale=1280:-2,fade=t=in:st={reveal:.3f}:d=1.5[v]")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-ss", f"{at:.3f}", "-t", f"{length:.3f}",
         "-i", described, "-filter_complex", fade, "-map", "[v]", "-map", "0:a",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         hero], check=True)
    return without, hero


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aloud.clip")
    ap.add_argument("film", help="the original film")
    ap.add_argument("out_dir", help="the pipeline's output, with described.mp4")
    ap.add_argument("--at", type=float, required=True)
    ap.add_argument("--length", type=float, default=16.0)
    ap.add_argument("--reveal", type=float, default=8.0)
    ap.add_argument("--dest", default=None)
    a = ap.parse_args(argv)
    dest = a.dest or os.path.join(a.out_dir, "video")
    w, h = cut(a.film, os.path.join(a.out_dir, "described.mp4"), a.at, a.length,
               a.reveal, dest)
    print(f"wrote {w}\nwrote {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
