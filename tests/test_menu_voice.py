"""The menu's spoken clips: one per setting value, all present, all in the
table the app reads.

The app plays `/pkg/assets/ui/<key>.m4a` for each key in tv/src/data/ui.json.
A key with no clip is a setting that goes silent on the device, which is the
exact failure these clips exist to fix, and nothing on Linux would notice it.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.menu_voice import clip_path, speak_menu, table

from test_publish import Voice

APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tv")


def test_every_setting_value_has_its_clip_in_the_app():
    keys = table(APP)
    assert len(keys) >= 11, keys
    missing = [k for k in keys if not os.path.exists(clip_path(APP, k))]
    assert not missing, f"no clip for {missing}: run python3 -m aloud.menu_voice"
    print(f"PASS all {len(keys)} menu clips are in the app")


def test_the_generator_writes_one_clip_per_key():
    d = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(d, "src", "data"))
        shutil.copy(os.path.join(APP, "src", "data", "ui.json"),
                    os.path.join(d, "src", "data", "ui.json"))
        written = speak_menu(d, synth=Voice())
        assert sorted(written) == sorted(clip_path(d, k) for k in table(APP))
        assert all(os.path.getsize(p) > 0 for p in written)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("PASS the generator writes one clip per key")


def test_each_clip_starts_with_the_setting_it_names():
    for key, words in table(APP).items():
        first = {"narration": "Narration", "level": "Voice level",
                 "menus": "Read the menu aloud", "density": "How much is said",
                 "picture": "Picture"}[key.split("-")[0]]
        assert words.startswith(first + ","), (key, words)
    print("PASS every clip says which setting it is first")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
