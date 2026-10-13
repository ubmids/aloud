"""The last check on a sentence before it is spoken: does it finish, and is it
about the picture rather than about the film.

Two kinds of cue shipped that the rest of the pipeline let through.

"A red-haired figure stands in a sunlit." (Sintel, 156 s) ends on an adjective
whose noun never arrives. The truncation rules only ran when the pipeline cut a
sentence; this one came from the model already broken, so nothing looked at it.

"The Blender Foundation Presents logo appears...", "The camera focuses on...",
"A close-up of a brown animated rabbit...", "...previously stretching, now...":
sentences about the film as a made object. The README promised they were
refused; only the narrowest of them ("Text appears on screen.") was.

Every sentence in these tests is one a real model wrote for a film on the shelf.
"""
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.budget import dangles
from aloud.caption import clean, meta, unfit
from aloud.publish import publish

from test_publish import Voice, tone


def test_a_sentence_that_stops_before_its_noun_is_caught():
    for said in ("A red-haired figure stands in a sunlit.",
                 "A man in a grey.",
                 "Smoke rises over a misty.",
                 "She walks through a dimly-lit.",
                 "A figure crouches beside the glowing.",
                 "The rabbit sits under a large, leafy.",
                 "The soldier looks toward the."):
        assert dangles(said), said
    print("PASS a sentence that stops before its noun is caught")


def test_a_sentence_that_finishes_is_not():
    for said in ("A red-haired figure stands in a sunlit alleyway.",
                 "A figure in snow.",
                 "The rabbit sits in the dark.",
                 "A woman switches off the light.",
                 "The ship climbs into the open.",
                 "A girl holds a puppy.",
                 "A man stands on the landing.",
                 "The sky is blue.",
                 "On screen: 40 YEARS LATER.",
                 "Two engines fire."):
        assert not dangles(said), said
    print("PASS a finished sentence is left alone")


def test_every_shipped_cue_that_finishes_still_passes():
    # The gate must not cost the shelf its good cues: of everything that
    # shipped before it existed, only the one broken cue is caught.
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    films = os.path.join(here, "tv", "src", "data", "films")
    caught = []
    for name in sorted(os.listdir(films)):
        with open(os.path.join(films, name)) as f:
            for c in json.load(f)["cues"]:
                if dangles(c["text"]):
                    caught.append(c["text"])
    assert caught in ([], ["A red-haired figure stands in a sunlit."]), caught
    print("PASS no finished cue on the shelf is caught as unfinished")


def test_sentences_about_the_film_rather_than_in_it_are_caught():
    for said in ("The Blender Foundation Presents logo appears centered on a dark, "
                 "snowy, mountainous landscape.",
                 "The camera focuses on a vast, textured expanse of rough rock.",
                 "A close-up of a brown rabbit with wide eyes.",
                 "The fluffy white rabbit, previously stretching, now looks up.",
                 "A grey mouse holds a green apple against scrolling white credit text.",
                 "A pink butterfly flutters near white text on a brown background.",
                 "The white rabbit's face fills the frame.",
                 "A dark, curved object enters the frame from the left.",
                 "A figure runs across rocky terrain in a fast-moving, low-angle shot.",
                 "Text appears on screen."):
        assert meta(said), said
    for said in ("A woman reads the text on a screen.",
                 "Text on a wall reads Leave now.",
                 "A soldier is shot and falls.",
                 "A photographer raises a camera.",
                 "On screen: Peach Open Movie Team.",
                 "The rabbit frames the squirrel's face with its paws.",
                 "Three rodents stand on a sunlit dirt path."):
        assert not meta(said), said
    print("PASS sentences about the film are caught, sentences in it are not")


def test_animated_and_cartoon_are_dropped_not_the_sentence():
    # The model calls every creature in an animated film "animated". The
    # creature is worth the gap; the word is not.
    assert clean("Three animated rodents stand on a sunlit dirt path.") == \
        "Three rodents stand on a sunlit dirt path."
    assert clean("A grey cartoon mouse with pink ears holds a green apple.") == \
        "A grey mouse with pink ears holds a green apple."
    assert clean("A cartoon squirrel hangs upside down.") == \
        "A squirrel hangs upside down."
    assert not meta(clean("A small, brown and white animated squirrel stands."))
    print("PASS 'animated' and 'cartoon' are dropped, the sentence is kept")


def test_unfit_names_the_reason():
    assert unfit("A red-haired figure stands in a sunlit.") == "it stops before its noun"
    assert unfit("The camera pans across the hills.") == "it is about the film, not in it"
    assert unfit("A red-haired figure stands in a sunlit alleyway.") is None
    print("PASS the gate says why it refused")


def test_publish_refuses_a_cue_that_would_be_read_out_broken():
    for text in ("A red-haired figure stands in a sunlit.",
                 "The camera focuses on a vast, textured expanse of rock."):
        d = tempfile.mkdtemp()
        try:
            out, app = os.path.join(d, "out"), os.path.join(d, "app")
            os.makedirs(out)
            audio = tone(os.path.join(out, "c1.wav"))
            with open(os.path.join(out, "description.json"), "w") as f:
                json.dump({"source": "", "cues": [
                    {"start": 1.0, "end": 2.0, "text": text, "audio": audio,
                     "gap": [1.0, 3.0]}]}, f)
            try:
                publish(out, "sintel-trailer", app, synth=Voice())
                raise AssertionError(f"published {text!r}")
            except ValueError as e:
                assert "1.0s" in str(e), e
                assert not os.path.exists(os.path.join(app, "src", "data"))
        finally:
            shutil.rmtree(d, ignore_errors=True)
    print("PASS publish refuses a cue that stops early or talks about the film")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
