"""The app's menu, spoken.

    python3 -m aloud.menu_voice [--app tv]

Every setting in the app says its name and value when it takes focus, and its
new value when select changes it (see tv/src/menuVoice.ts). The device does no
speech synthesis, so each of those sentences is a clip made here, in the same
voice as the descriptions, from the words in tv/src/data/ui.json: one table,
read by both sides, so a clip cannot say something its key does not.
"""
import argparse
import json
import os
import sys
import tempfile

from .publish import _m4a
from .synth import Synth


def table(app: str) -> dict:
    with open(os.path.join(app, "src", "data", "ui.json")) as f:
        return json.load(f)


def clip_path(app: str, key: str) -> str:
    return os.path.join(app, "assets", "ui", f"{key}.m4a")


def speak_menu(app: str = "tv", synth=None) -> list[str]:
    synth = synth or Synth()
    work = tempfile.mkdtemp(prefix="aloud-menu-")
    written = []
    for key, words in table(app).items():
        spoken = synth.speak(words, out_dir=os.path.join(work, key))
        dest = clip_path(app, key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        _m4a(spoken.path, dest)
        written.append(dest)
    return written


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aloud.menu_voice")
    ap.add_argument("--app", default="tv")
    a = ap.parse_args(argv)
    for path in speak_menu(a.app):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
