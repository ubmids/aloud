"""The demo video with Subomi's narration (ElevenLabs, his approved voice),
cut from the Vega Virtual Device recordings in docs/video/assets/.

    python3 docs/video/narrated.py [--out=FILE] [--estimate]

aloud's own voice is the product, so it is never talked over: every narration
line sits in a gap around the app's descriptions and announcements (times
measured from the recordings), and the film dips under the narration.

Each line is one ElevenLabs request, cached by its text in
~/Desktop/hackathons/aloud-video/voice/, so a rebuild costs nothing and a bad
take is redone alone. The key is read from ~/.config/elevenlabs/key and never
written anywhere.

Writes ~/Desktop/hackathons/aloud-video/aloud-narrated.mp4, .srt (the
narration, for the upload) and .json (each chunk and line time).
"""
import os
import pathlib
import subprocess
import sys

from PIL import Image, ImageFilter, ImageEnhance

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import narrate  # noqa: E402
import voice  # noqa: E402

A = HERE / "assets"
VIDEO = pathlib.Path.home() / "Desktop/hackathons/aloud-video"

# What Subomi says. No claim here goes beyond what the recordings show.
# Say "aloud" like the word.
LINES = {
    "hi": "Hey, I'm Subomi. I built aloud, a Fire TV app that tells you what's on "
          "screen, in the gaps between the dialogue.",
    "hi2": "So, let me show you. Here's a film, with the picture off.",
    "that": "That's aloud talking.",
    "there": "And there's the ship. Exactly as it said.",
    "who1": "Most of us watch TV without really looking at it, half the time. Cooking, "
            "ironing, a toddler on your lap.",
    "who2": "And some people can't see the screen at all. That's who I built it for first.",
    "vvd": "This is aloud running on the Vega Virtual Device, the Fire TV simulator. Every "
           "title and every setting is read out loud, so you can use it with your eyes shut.",
    "shelf": "It reads each film to you as you land on it.",
    "play": "So I pick Tears of Steel. Watch the bar at the bottom. aloud only speaks "
            "inside the quiet gaps.",
    "off": "Narration off, for whoever doesn't need it.",
    "menu": "And Menu repeats the last line, for whoever does.",
    "how": "So how does it work? Ahead of time, aloud finds every silence in the "
           "dialogue. A vision model looks at each one and writes one sentence that fits.",
    "how2": "Each sentence is spoken and measured before it goes in. So the TV itself does "
            "no AI work at all, and a person can check every line.",
    "lib": "I also split the player out as an open library, so other Vega apps can play "
           "a described track too.",
    "close": "Look away, close your eyes, or never see the screen at all. aloud keeps you "
             "in the film. Thanks for watching.",
}


def spoken(k):
    # The voice reads "aloud" as the word; lowercase at a sentence start is fine.
    return LINES[k]


def still(src, at, name, soft=False):
    out = VIDEO / "narrated-work" / f"still-{name}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    narrate.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{at:.2f}", "-i", str(src),
                 "-frames:v", "1", "-vf", "scale=1920:1080", str(out)])
    if soft:
        im = Image.open(out).convert("RGB").filter(ImageFilter.GaussianBlur(14))
        ImageEnhance.Brightness(im).enhance(0.55).save(out)
    return out


def over(base, card, name):
    """A transparent-backed card over a still: the card's black is dropped by
    blending with lighten, as cut.py does."""
    out = VIDEO / "narrated-work" / f"{name}.png"
    b = Image.open(base).convert("RGB").resize((1920, 1080))
    c = Image.open(card).convert("RGB").resize((1920, 1080))
    from PIL import ImageChops
    ImageChops.lighter(b, c).save(out)
    return out


def plan():
    cold, shelf, player = A / "01-cold-open.mp4", A / "02-shelf.mp4", A / "03-player.mp4"
    shelf0 = still(shelf, 1.0, "shelf")
    title = over(still(shelf, 1.0, "shelf-soft", soft=True), A / "card-02-title.png", "title")
    return [
        # Who I am, over the title card on the (blurred) device shelf.
        dict(name="hi", src=title, lines=["hi", "hi2"], gap=0.5),
        # The cold open, untouched: black, the film, aloud's two descriptions,
        # then the picture fades up on exactly what was said.
        dict(name="cold", src=cold, ss=0.0, to=22.6, fixed=True, keep=1.0, duck=0.35,
             hold=1.8, lines=["that", "there"], at={"that": 11.4, "there": 20.0},
             overlays=[(A / "card-01-picture-off.png", 0.0, 8.6)]),
        dict(name="who", src=A / "card-03-who.png", lines=["who1", "who2"], gap=0.45),
        dict(name="vvd", src=shelf0, lines=["vvd"]),
        # The shelf reads Sintel, then Big Buck Bunny (app speech 3.3-7.9, 15.0-20.5).
        dict(name="shelf", src=shelf, ss=1.5, to=21.0, fixed=True, keep=1.0,
             lines=["shelf"], at={"shelf": 8.3 - 1.5 + 0.1}),
        # The player. Descriptions at 8.7-15.0 and 16.1-19.2, "Narration off"
        # announced 22.2-25.4, Menu repeats the last line 30.0-32.8.
        dict(name="player", src=player, ss=0.0, to=40.4, fixed=True, keep=1.0, duck=0.3,
             lines=["play", "off", "menu"], at={"play": 0.4, "off": 25.7, "menu": 33.1}),
        dict(name="how", src=A / "card-04-how.png", lines=["how", "how2"], gap=0.5),
        dict(name="lib", src=A / "card-05-library.png", lines=["lib"]),
        dict(name="close", src=A / "card-06-end.png", lines=["close"], tail=2.5),
    ]


# aloud's own voice in the recordings, for the captions (clip time, from a
# word-timed transcript; text from the track and ui.json, not the transcript).
APP_SPEECH = {
    "cold": [(8.92, 10.82, "Flying ship descends lower."),
             (15.03, 19.50, "The flying ship continues descending toward the residential "
                            "buildings below.")],
    "shelf": [(3.26, 7.94, "Sintel. Fantasy, 2010, 15 minutes. 41 descriptions."),
              (14.98, 20.54, "Big Buck Bunny. Family comedy, 2008, 10 minutes. "
                             "47 descriptions.")],
    "player": [(8.72, 15.02, "A human brain sits on a white platform surrounded by glowing "
                             "pink circular light rings."),
               (16.10, 19.20, "The flying ship hovers above the sprawling city below."),
               (20.06, 21.72, "Inside the flying ship,"),
               (22.18, 25.38, "Narration, off. Films play with their own sound only."),
               (30.02, 32.80, "A hand holds an open newspaper.")],
}


def add_app_speech(final, report, clips):
    """Merge aloud's own lines, marked [aloud], into the narration .srt."""
    import re
    srt = final.with_suffix(".srt")
    cues = []
    for block in srt.read_text().strip().split("\n\n"):
        _, times, text = block.split("\n", 2)
        cues.append((times, text))
    ts = lambda x: narrate.stamp(x)
    for r in report:
        for a, b, text in APP_SPEECH.get(r["chunk"], []):
            off = r["start"] - clips[r["chunk"]]
            cues.append((f"{ts(off + a)} --> {ts(off + b)}", f"[aloud] {text}"))
    cues.sort(key=lambda c: c[0])
    srt.write_text("\n".join(f"{i}\n{t}\n{x}\n" for i, (t, x) in enumerate(cues, 1)))


def main(argv):
    opts = dict(a.split("=", 1) for a in argv if a.startswith("--") and "=" in a)
    final = pathlib.Path(os.path.expanduser(opts.get("--out", VIDEO / "aloud-narrated.mp4")))
    chars = sum(len(spoken(k)) for k in LINES)
    print(f"{len(LINES)} lines, {chars} characters, about {chars / 13.5:.0f} s of speech")
    if "--estimate" in argv:
        return 0
    cache = VIDEO / "voice"
    total, report = narrate.build(plan(), {k: (v, spoken(k)) for k, v in LINES.items()},
                                  lambda text: voice.line(text, cache),
                                  VIDEO / "narrated-work", final)
    add_app_speech(final, report, {"cold": 0.0, "shelf": 1.5, "player": 0.0})
    for r in report:
        print(f"{r['start']:7.2f}  {r['seconds']:6.2f}s  {r['chunk']:8} {r['source']}")
    print(f"\n{final}\n{total:.1f} s ({int(total // 60)}:{total % 60:04.1f})"
          + ("   OVER 2:55, cut something" if total > 175 else "   under 3:00"))
    print(f"ElevenLabs characters spent so far (all takes): {voice.spent(cache)}")
    for p in (VIDEO / "narrated-work").glob("*.mp4"):
        p.unlink()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
