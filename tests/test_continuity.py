"""The continuity pass, with a fake text model and a fake voice.

No model runs here. What is tested is everything around the model: that a
revision is kept only when it passes the same rules as the first draft, that
the original is kept beside it, and that nothing is on unless asked for.
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud import continuity
from aloud.captions import lines
from aloud.films import BY_ID
from aloud.synth import Spoken
from aloud.track import Cue, Track


class Voice:
    """Speaks at a fixed 0.3 s a word, so fitting is predictable."""
    def speak(self, text, out_dir=None):
        return Spoken(text, f"/tmp/{len(text)}.wav", 0.3 * len(text.split()))


class Model:
    label = "fake-model (continuity pass)"

    def __init__(self, revisions):
        self.revisions, self.asked = revisions, []

    def __call__(self, system, user):
        self.asked.append((system, user))
        return json.dumps([{"n": n, "text": t} for n, t in self.revisions.items()])


def track():
    return Track(cues=[
        Cue(10.0, 11.5, "An elderly person reads a newspaper.", "a.wav", (10.0, 13.0)),
        Cue(20.0, 21.5, "Young man stands before giant construct.", "b.wav", (20.0, 23.0)),
        Cue(30.0, 30.9, "A robot falls.", "c.wav", (30.0, 31.0)),
        Cue(40.0, 41.0, "A woman waves.", "d.wav", (40.0, 42.0)),
    ])


def test_a_consistent_revision_is_kept_with_its_draft():
    t = track()
    model = Model({1: "Thom reads a newspaper.",
                   2: "A young man stands before a giant construct."})
    log = continuity.revise(t, rewriter=model, synth=Voice(),
                            cast=BY_ID["tears-of-steel"].cast)
    assert [o for _, o in log] == ["revised", "revised", "unchanged", "unchanged"], log
    assert t.cues[0].text == "Thom reads a newspaper."
    assert t.cues[0].draft == "An elderly person reads a newspaper."
    assert t.cues[0].audio == "/tmp/23.wav"
    assert abs(t.cues[0].end - 11.2) < 1e-6
    assert t.revised_by == "fake-model (continuity pass)"
    d = t.to_dict()
    assert d["revised_by"] == "fake-model (continuity pass)"
    assert d["cues"][1]["draft"] == "Young man stands before giant construct."
    assert "draft" not in d["cues"][2]
    print("PASS a consistent revision is kept, and the draft is kept beside it")


def test_a_revision_that_breaks_a_rule_keeps_the_original():
    t = track()
    model = Model({
        1: "Gandalf reads a newspaper.",                         # not in the cast
        2: "The camera finds a young man before a construct.",   # about the film
        3: "A robot falls down hard.",                          # past its gap
        4: "A woman with dreadlocks waves at the soldiers on the wall.",  # longer
    })
    log = continuity.revise(t, rewriter=model, synth=Voice(),
                            cast=BY_ID["tears-of-steel"].cast)
    assert [o for _, o in log] == [
        "it names someone the cast list does not",
        "it is about the film, not in it",
        "it no longer fits its gap",
        "it is longer than the original"], log
    assert [c.text for c in t.cues] == [c.text for c in track().cues]
    assert all(c.draft is None for c in t.cues)
    print("PASS a revision that breaks any rule leaves the original in place")


def test_the_model_is_shown_the_cast_the_dialogue_and_every_cue():
    model = Model({})
    continuity.revise(track(), rewriter=model, synth=Voice(),
                      cast="Thom: a man.", dialogue=[(5.0, 6.0, "Look Celia.")])
    system, user = model.asked[0]
    assert "Do not add any action" in system
    assert "Cast: Thom: a man." in user
    assert "Look Celia." in user
    assert "4. [40.0s, at most 3 words plus articles] A woman waves." in user
    print("PASS the model sees the whole track, the dialogue and the cast")


def test_a_reply_wrapped_in_a_fence_or_junk_is_survivable():
    assert continuity.parse('```json\n[{"n": 1, "text": "A."}]\n```', 2) == {1: "A."}
    assert continuity.parse('Sure! [{"n": 2, "text": "B."}] done', 2) == {2: "B."}
    assert continuity.parse("no json here", 2) == {}
    assert continuity.parse('[{"n": 9, "text": "C."}]', 2) == {}
    print("PASS a messy reply is read where possible and ignored otherwise")


def test_cast_names_come_from_the_cast_list():
    assert continuity.cast_names(BY_ID["tears-of-steel"].cast) == {
        "Thom", "Celia", "Barley", "Captain"}
    assert continuity.cast_names(BY_ID["sintel"].cast) == {"Sintel", "Scales"}
    assert continuity.new_names("A man waves.", "Thom waves.", {"Thom"}) == set()
    assert continuity.new_names("A man waves.", "Bob waves.", {"Thom"}) == {"Bob"}
    assert continuity.new_names("On screen: 40 YEARS LATER.",
                                "On screen: 40 YEARS LATER.", set()) == set()
    print("PASS names come only from the cast list")


def test_it_is_off_unless_asked_for():
    old = os.environ.pop("ALOUD_CONTINUITY", None)
    try:
        assert not continuity.enabled()
        os.environ["ALOUD_CONTINUITY"] = "1"
        assert continuity.enabled()
    finally:
        os.environ.pop("ALOUD_CONTINUITY", None)
        if old is not None:
            os.environ["ALOUD_CONTINUITY"] = old
    print("PASS the pass is off by default")


def test_caption_lines_carry_their_words():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "c.srt")
    with open(p, "w") as f:
        f.write("1\n00:00:05,000 --> 00:00:06,500\nYou're a jerk,\nThom.\n\n"
                "2\n00:01:40,000 --> 00:01:41,000\nShouldn't you be down there?\n")
    assert lines(p) == [(5.0, 6.5, "You're a jerk, Thom."),
                        (100.0, 101.0, "Shouldn't you be down there?")]
    print("PASS caption lines are read with their words")


def test_tears_of_steel_now_has_a_cast():
    cast = BY_ID["tears-of-steel"].cast
    for name in ("Thom", "Celia", "Barley", "Captain"):
        assert name in cast, name
    print("PASS Tears of Steel names its people, as its dialogue does")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
