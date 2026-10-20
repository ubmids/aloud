"""Assemble the whole demo video from the pre-rendered assets, with no editor.

    python3 docs/video/cut.py [--inserts=DIR] [--out=FILE] [--say]

Everything that does not need a person is already in docs/video/assets/
(SHOTS.md). This script cuts it together in the order of video/SCRIPT.md and
lays in whatever the owner has recorded. Drop files into the inserts folder
(default ~/Desktop/hackathons/aloud-video/inserts) and run it again:

  n-who.m4a  n-everyone.m4a  n-shelf.m4a  n-player.m4a  n-how.m4a
  n-new.m4a  n-library.m4a  n-close.m4a
        voiceover lines (Voice Memos is fine; m4a, wav, aiff, mp3, caf)
  oncam-who.mp4 / oncam-close.mp4
        optional: the owner to camera; replaces the card under that line
  viewer.mp4
        optional: the viewer session, already cut to 20 to 30 s

A line with no recording is shown as an on-screen caption instead, so the
video is complete and honest with zero recordings (no robot voice, nothing
marked PLACEHOLDER). `--say` uses macOS `say` for missing lines instead, for
checking timing only; never upload that version.

Writes the video (default ~/Desktop/hackathons/aloud-video/aloud-demo.mp4),
an .srt of the voiceover next to it, and prints each segment and the total.
Needs only ffmpeg and Pillow.
"""
import json
import os
import pathlib
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent
A = HERE / "assets"
FONT = ROOT / "tv" / "assets" / "fonts" / "AtkinsonHyperlegibleNext-SemiBold.ttf"
W, H, FPS = 1920, 1080, 30
ENC = ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
       "-r", str(FPS), "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]
DUCK = 0.3          # how far the app's sound dips under the voiceover

# The voiceover, in plain spoken English. Keep in step with video/SCRIPT.md.
LINES = {
    "who": "I'm Subomi. I built aloud. A Fire TV app that tells you what's on "
           "screen, in the gaps between the dialogue.",
    "everyone": "Most of us watch TV without looking at it half the time.",
    "shelf": "Every title and every setting is read out loud, so you can use it "
             "with your eyes shut.",
    "player": "Narration off, for whoever doesn't need it. One button repeats "
              "the last description, for whoever does.",
    "how": "Ahead of time, aloud finds every silence in the dialogue. A vision "
           "model looks at each one, and writes one sentence that fits it. Each "
           "sentence is spoken and measured before it goes in. Across the whole "
           "film, the voice touches dialogue for under a second.",
    "new": "Prime Video uses AI to help its writers find the gaps. aloud is the "
           "TV half. An app a blind viewer can run alone, that never starts a "
           "sentence the silence can't hold. It's all made ahead of time, so a "
           "person can check every line.",
    "library": "The player is a library. Any Vega app can play a described track.",
    "close": "Look away, close your eyes, or never see the screen at all. aloud "
             "keeps you in the film.",
}


def run(cmd):
    subprocess.run(cmd, check=True)


def duration(p) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout
    return float(out.strip())


def first(d: pathlib.Path, stem: str, exts):
    for e in exts:
        p = d / f"{stem}.{e}"
        if p.exists():
            return p
    return None


def wrap(draw, text, font, width):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= width:
            cur = t
        else:
            lines.append(cur)
            cur = w
    return lines + [cur] if cur else lines


def caption_png(text, out, size=46, top=False):
    """A caption box in the style of assets/caption.png, bottom left."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f = ImageFont.truetype(str(FONT), size)
    lines = wrap(d, text, f, 1500)
    lh, pad = int(size * 1.3), 26
    box_w = max(d.textlength(l, font=f) for l in lines) + 2 * pad
    box_h = lh * len(lines) + 2 * pad
    x, y = 64, (64 if top else H - 64 - box_h)
    d.rectangle([x, y, x + box_w, y + box_h], fill=(17, 17, 17, 235))
    d.rectangle([x, y, x + 8, y + box_h], fill=(150, 150, 150, 255))  # grey: yellow means aloud is speaking (DESIGN rule 3)
    for i, l in enumerate(lines):
        d.text((x + pad + 6, y + pad + i * lh), l, font=f, fill=(255, 255, 255, 255))
    img.save(out)
    return out


class Cut:
    def __init__(self, inserts: pathlib.Path, work: pathlib.Path, say: bool):
        self.inserts, self.work, self.say = inserts, work, say
        work.mkdir(parents=True, exist_ok=True)
        self.parts, self.srt = [], []

    def voice(self, key):
        """(audio or None, seconds, how): a real recording, a `say` check, or
        a caption with the reading time."""
        real = first(self.inserts, f"n-{key}", ("m4a", "wav", "aiff", "mp3", "caf"))
        if real:
            return real, duration(real), "voice"
        if self.say:
            p = self.work / f"say-{key}.aiff"
            run(["say", "-v", "Daniel", "-r", "175", "-o", str(p), LINES[key]])
            return p, duration(p), "say"
        words = len(LINES[key].split())
        return None, max(2.5, words / 2.6 + 1.0), "caption"

    def _add(self, name, path, source, how="", vo_at=None, vo_len=0.0, key=None):
        secs = duration(path)
        start = sum(r["seconds"] for _, r in self.parts)
        if key is not None and vo_at is not None:
            self.srt.append((start + vo_at, start + vo_at + vo_len, LINES[key]))
        self.parts.append((path, {"segment": name, "source": source,
                                  "seconds": round(secs, 2), "line": how}))

    def _mix(self, cmd, inputs_v, graph_v, vo, vo_at, end, app_audio=True):
        """Shared tail: duck the app's audio under the voiceover and mix it in."""
        n_in = inputs_v
        graph = graph_v                  # appended to in place
        if app_audio:
            graph.append("[0:a]apad[pa]")
            a = "[pa]"
        else:
            cmd += ["-f", "lavfi", "-t", f"{end:.2f}", "-i", "anullsrc=r=48000:cl=stereo"]
            a = f"[{n_in}:a]"
            n_in += 1
        if vo:
            vo_audio, vo_len = vo
            cmd += ["-i", str(vo_audio)]
            graph.append(f"{a}volume={DUCK}:enable='between(t,{vo_at:.2f},{vo_at + vo_len:.2f})'[d];"
                         f"[{n_in}:a]adelay={int(vo_at * 1000)}:all=1,volume=1.6[n];"
                         f"[d][n]amix=inputs=2:normalize=0:duration=first[a]")
            return "[a]"
        graph.append(f"{a}anull[a]")
        return "[a]"

    def footage(self, name, src, ss, to, overlays=(), key=None, vo_at=0.5,
                lighten=None, hold_end=0.0):
        """A stretch of a recording, with optional overlays (png, from, to),
        a voiceover line at vo_at, and a card blended in light over black."""
        out = self.work / f"{len(self.parts):02d}-{name}.mp4"
        length = to - ss + hold_end
        cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ss:.3f}", "-to", f"{to:.3f}",
               "-i", str(src)]
        ov = list(overlays)
        audio, secs, how = (None, 0.0, "")
        if key:
            audio, secs, how = self.voice(key)
            if how == "caption":
                ov.append((caption_png(LINES[key], self.work / f"cap-{key}.png"),
                           vo_at, vo_at + secs))
        v = "[0:v]"
        hold = f",tpad=stop_mode=clone:stop_duration={hold_end:.2f}" if hold_end else ""
        graph = [f"{v}scale={W}:{H},fps={FPS},format=yuv420p{hold}[v0]"]
        v, k = "[v0]", 1
        if lighten:
            png, a, b = lighten
            cmd += ["-loop", "1", "-t", f"{length:.2f}", "-i", str(png)]
            graph.append(f"[{k}:v]format=yuv420p,fps={FPS}[l{k}];"
                         f"{v}[l{k}]blend=all_mode=lighten:enable='between(t,{a},{b})'[vb]")
            v, k = "[vb]", k + 1
        for i, (png, a, b) in enumerate(ov):
            cmd += ["-i", str(png)]
            graph.append(f"{v}[{k}:v]overlay=0:0:enable='between(t,{a:.2f},{b:.2f})'[o{i}]")
            v, k = f"[o{i}]", k + 1
        a_out = self._mix(cmd, k, graph, (audio, secs) if audio else None, vo_at, length)
        cmd += ["-filter_complex", ";".join(graph), "-map", v, "-map", a_out]
        run(cmd + ENC + ["-t", f"{length:.2f}", str(out)])
        self._add(name, out, f"{pathlib.Path(src).name} {ss:g}-{to:g}s", how,
                  vo_at if key else None, secs, key)

    def card(self, name, png, key=None, hold=0.8, base=None, min_secs=0.0, dim=False,
             cap_top=False):
        """A still (a card, or a card over a still frame) for as long as its
        line takes, plus `hold`."""
        out = self.work / f"{len(self.parts):02d}-{name}.mp4"
        audio, secs, how = self.voice(key) if key else (None, 0.0, "")
        length = max(min_secs, secs + hold + 0.4)
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        graph, k = [], 0
        if base:
            cmd += ["-loop", "1", "-t", f"{length:.2f}", "-i", str(base)]
            cmd += ["-loop", "1", "-t", f"{length:.2f}", "-i", str(png)]
            soft = ",boxblur=18:2,eq=brightness=-0.22" if dim else ""
            graph.append(f"[0:v]scale={W}:{H}{soft}[b];[b][1:v]overlay=0:0,fps={FPS},format=yuv420p[c]")
            k = 2
        else:
            cmd += ["-loop", "1", "-t", f"{length:.2f}", "-i", str(png)]
            graph.append(f"[0:v]scale={W}:{H},fps={FPS},format=yuv420p[c]")
            k = 1
        v = "[c]"
        if how == "caption":
            cmd += ["-loop", "1", "-t", f"{length:.2f}", "-i",
                    str(caption_png(LINES[key], self.work / f"cap-{key}.png", top=cap_top))]
            graph.append(f"{v}[{k}:v]overlay=0:0:enable='between(t,0.4,{0.4 + secs:.2f})'[cc]")
            v, k = "[cc]", k + 1
        a_out = self._mix(cmd, k, graph, (audio, secs) if audio else None, 0.4, length,
                          app_audio=False)
        cmd += ["-filter_complex", ";".join(graph), "-map", v, "-map", a_out]
        run(cmd + ENC + ["-t", f"{length:.2f}", str(out)])
        self._add(name, out, pathlib.Path(png).name, how, 0.4 if key else None, secs, key)

    def insert(self, name, clip, key=None):
        """Real footage of a person, fitted to 1920x1080 with its own sound."""
        out = self.work / f"{len(self.parts):02d}-{name}.mp4"
        fit = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,"
               f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=0x0b0b0b,fps={FPS},format=yuv420p")
        run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(clip), "-vf", fit] + ENC + [str(out)])
        self._add(name, out, pathlib.Path(clip).name, "on camera")

    def still(self, src, at, name):
        p = self.work / f"still-{name}.png"
        run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", str(src),
             "-frames:v", "1", str(p)])
        return p

    def finish(self, final: pathlib.Path):
        lst = self.work / "list.txt"
        lst.write_text("".join(f"file '{p}'\n" for p, _ in self.parts))
        run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
             "-c", "copy", "-movflags", "+faststart", str(final)])

        def stamp(t):
            ms = int(round(t * 1000))
            return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
        srt = []
        for i, (a, b, text) in enumerate(self.srt, 1):
            srt += [str(i), f"{stamp(a)} --> {stamp(b)}", text, ""]
        final.with_suffix(".srt").write_text("\n".join(srt))
        recs = [r for _, r in self.parts]
        total = duration(final)
        final.with_suffix(".json").write_text(json.dumps(
            {"total_seconds": round(total, 2), "segments": recs}, indent=1))
        return total, recs


def main(argv):
    opts = dict(a.split("=", 1) for a in argv if a.startswith("--") and "=" in a)
    inserts = pathlib.Path(os.path.expanduser(
        opts.get("--inserts", "~/Desktop/hackathons/aloud-video/inserts"))).resolve()
    final = pathlib.Path(os.path.expanduser(
        opts.get("--out", "~/Desktop/hackathons/aloud-video/aloud-demo.mp4"))).resolve()
    final.parent.mkdir(parents=True, exist_ok=True)
    inserts.mkdir(parents=True, exist_ok=True)
    for need in ("01-cold-open.mp4", "02-shelf.mp4", "03-player.mp4", "card-02-title.png"):
        if not (A / need).exists():
            raise SystemExit(f"missing docs/video/assets/{need}: see docs/video/SHOTS.md")
    cut = Cut(inserts, final.parent / "work", "--say" in argv)

    # 0:00 cold open: black, the film's sound and aloud's voice, then the picture.
    cut.footage("cold", A / "01-cold-open.mp4", 0.0, 20.0,
                lighten=(A / "card-01-picture-off.png", 0, 11.5))
    shelf0 = cut.still(A / "02-shelf.mp4", 1.0, "shelf")
    # Who made it: on camera if filmed, else the title over the shelf.
    clip = first(inserts, "oncam-who", ("mp4", "mov", "m4v"))
    if clip:
        cut.insert("who", clip)
    else:
        cut.card("who", A / "card-02-title.png", key="who", base=shelf0, dim=True,
                 cap_top=True)
    # For everyone.
    cut.card("everyone", A / "card-03-who.png", key="everyone", min_secs=4.0)
    blank = cut.work / "blank.png"
    Image.new("RGBA", (W, H), (0, 0, 0, 0)).save(blank)
    cut.card("shelf-intro", blank, key="shelf", base=shelf0, hold=0.3)
    # The shelf reads Sintel and Big Buck Bunny out loud, then back.
    cut.footage("shelf", A / "02-shelf.mp4", 1.5, 24.0)
    # The player: a description and the dip, narration off, Menu repeats.
    p_len = duration(A / "03-player.mp4")
    cut.footage("player", A / "03-player.mp4", 0.0, min(p_len, 40.5), key="player", vo_at=22.9)
    # A viewer, only if one was filmed with consent (PEOPLE.md).
    clip = first(inserts, "viewer", ("mp4", "mov", "m4v"))
    if clip:
        cut.insert("viewer", clip)
    # How it works.
    cut.card("how", A / "card-04-how.png", key="how", hold=1.2)
    # Why this is new, over the full-screen picture with its caption.
    _, secs, _ = cut.voice("new")
    # The cold open is black until about 16 s; start on the picture and hold
    # its last frame for as long as the line needs.
    cut.footage("new", A / "01-cold-open.mp4", 15.5, 22.6, key="new", vo_at=0.3,
                hold_end=max(0.0, secs + 1.0 - 7.1))
    cut.card("library", A / "card-05-library.png", key="library", hold=1.0)
    clip = first(inserts, "oncam-close", ("mp4", "mov", "m4v"))
    if clip:
        cut.insert("close", clip)
        cut.card("end", A / "card-06-end.png", min_secs=5.0)
    else:
        cut.card("close", A / "card-06-end.png", key="close", hold=4.0)

    total, recs = cut.finish(final)
    for r in recs:
        print(f"{r['seconds']:6.2f}s  {r['segment']:12} {r['line']:9} {r['source']}")
    left = [k for k in LINES if not first(inserts, f"n-{k}", ("m4a", "wav", "aiff", "mp3", "caf"))]
    print(f"\n{final}\n{total:.1f} s ({int(total // 60)}:{total % 60:04.1f})"
          + ("   OVER 2:59, cut something" if total > 178.5 else "   under 2:59"))
    if left:
        print(("say voice (do NOT upload) for: " if "--say" in argv else
               "shown as captions (no recording yet): ") + ", ".join(left))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
