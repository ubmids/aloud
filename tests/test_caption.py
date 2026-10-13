"""The vision describer, against a stub that speaks its protocol.

Same reasoning as Hearth's extraction tests: without a key this path would ship
never having executed, and the request shape, the image encoding and the
response cleaning would all be unverified.
"""
import base64
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.caption import (GeminiCaptioner, LocalCaptioner, VisionCaptioner,
                           captioner_from_env, clean)

STATE = {"reply": "A man crosses the empty street.", "status": 200, "req": None,
         "path": None, "headers": None}

PROVIDER_ENV = ("ALOUD_LLM_BASE_URL", "ALOUD_LLM_API_KEY", "ALOUD_LLM_MODEL",
                "GEMINI_API_KEY", "ALOUD_GEMINI_API_KEY", "ALOUD_GEMINI_MODEL",
                "ALOUD_GEMINI_BASE_URL", "ALOUD_LOCAL_VLM_URL",
                "ALOUD_LOCAL_VLM_MODEL", "ALOUD_VISION")


def clear_provider_env():
    for k in PROVIDER_ENV:
        os.environ.pop(k, None)
# Per-process, not a fixed path. Two copies of this suite running at once, as
# any mutation tester or parallel CI does, otherwise race on the same file.
FRAME = os.path.join(tempfile.gettempdir(), f"aloud_caption_frame_{os.getpid()}.jpg")
PNG_FRAME = FRAME.replace(".jpg", ".png")


class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        STATE["path"] = self.path
        STATE["headers"] = dict(self.headers)
        STATE["req"] = json.loads(self.rfile.read(
            int(self.headers.get("Content-Length", 0))))
        if STATE["status"] != 200:
            self.send_response(STATE["status"]); self.end_headers()
            self.wfile.write(b'{"error":"nope"}'); return
        if ":generateContent" in self.path:
            out = json.dumps({"candidates": [{"content": {"parts": [
                {"text": STATE["reply"]}]}, "finishReason": "STOP"}]}).encode()
        else:
            out = json.dumps({"choices": [{"message": {"content": STATE["reply"]}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers(); self.wfile.write(out)

    def log_message(self, *a):
        pass


SRV = HTTPServer(("127.0.0.1", 0), Stub)
threading.Thread(target=SRV.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{SRV.server_port}"


def make_frame(path=FRAME):
    import subprocess, shutil, atexit
    if os.path.exists(path):
        return True
    if not shutil.which("ffmpeg"):
        return False
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "color=c=navy:s=160x90:d=1", "-frames:v", "1", path],
                   check=True)
    atexit.register(lambda: os.path.exists(path) and os.remove(path))
    return True


def cap():
    return VisionCaptioner(base_url=BASE, api_key="k", model="stub-vision")


def test_the_frame_is_sent_as_an_image_not_a_path():
    """A path means nothing to the endpoint. Sending one would produce confident
    descriptions of an image the model never saw."""
    if not make_frame():
        print("SKIP no ffmpeg"); return
    cap()(FRAME, 10)
    content = STATE["req"]["messages"][1]["content"]
    img = next(c for c in content if c["type"] == "image_url")
    assert img["image_url"]["url"].startswith("data:image/"), img["image_url"]["url"][:40]
    payload = img["image_url"]["url"].split(",", 1)[1]
    assert len(base64.b64decode(payload)) > 100
    print("PASS the frame is embedded as a data URL, not referenced by path")


def test_the_word_target_reaches_the_model():
    if not make_frame():
        print("SKIP no ffmpeg"); return
    cap()(FRAME, 7)
    text = next(c for c in STATE["req"]["messages"][1]["content"]
                if c["type"] == "text")["text"]
    assert "7 words" in text, text
    print("PASS the word budget is in the prompt")


def test_the_conventions_are_in_the_system_prompt():
    if not make_frame():
        print("SKIP no ffmpeg"); return
    cap()(FRAME, 10)
    sysmsg = STATE["req"]["messages"][0]["content"].lower()
    for rule in ("present tense", "do not interpret", "can be heard",
                 "name characters"):
        assert rule in sysmsg, rule
    print("PASS the audio description conventions are instructed")


def test_model_preamble_is_stripped():
    assert clean('"The image shows a man crossing the street"') == \
        "A man crossing the street."
    assert clean("Description: She opens the door.") == "She opens the door."
    assert clean("the room is empty") == "The room is empty."
    assert clean("") == ""
    print("PASS preambles and quotes are stripped, sentences closed")


def test_a_failure_is_raised_not_papered_over():
    """The pipeline decides what to do when the describer fails. A captioner
    that returns something plausible on an API error turns a broken describer
    into a film full of confident nonsense."""
    if not make_frame():
        print("SKIP no ffmpeg"); return
    STATE["status"] = 500
    try:
        cap()(FRAME, 10)
        raise AssertionError("an API failure was swallowed")
    except AssertionError:
        raise
    except Exception:
        pass
    finally:
        STATE["status"] = 200
    print("PASS an API failure raises rather than inventing a description")


def test_with_no_endpoint_it_falls_back_visibly():
    clear_provider_env()
    c = captioner_from_env()
    assert not isinstance(c, VisionCaptioner)
    out = c("/nonexistent.jpg", 8)
    assert "scene changes" in out, out
    print("PASS with no endpoint the obvious stub is used, not a plausible fake")


# --- found by Mutiny -------------------------------------------------------
# The tests above check what is sent and never check what comes back, what the
# request is addressed to, or whether a captioner with half its configuration
# thinks it is ready. Each of these corresponds to a mutation they waved
# through.

def test_the_description_actually_comes_back():
    """Nothing asserted the return value, so the captioner could have returned
    None and every test above would still pass. The pipeline would then
    schedule a cue with no words in it."""
    if not make_frame():
        print("SKIP no ffmpeg"); return
    STATE["reply"] = "A woman waits at the window."
    try:
        assert cap()(FRAME, 10) == "A woman waits at the window."
    finally:
        STATE["reply"] = "A man crosses the empty street."
    print("PASS the cleaned description is returned to the caller")


def test_half_a_configuration_is_not_a_working_captioner():
    """`base_url and api_key`. With `or` a captioner holding a URL and no key
    reports itself ready, the pipeline uses it instead of the visible stub, and
    the failure arrives as an authentication error in the middle of a film."""
    assert not VisionCaptioner(base_url=BASE, api_key=None).available
    assert not VisionCaptioner(base_url=None, api_key="k").available
    assert VisionCaptioner(base_url=BASE, api_key="k").available
    print("PASS a captioner needs both an endpoint and a key to be available")


def test_the_configured_endpoint_is_used_when_there_is_one():
    """Only the no-key branch was tested, so `captioner_from_env` could have
    returned nothing at all on the path that matters in production."""
    clear_provider_env()
    os.environ["ALOUD_LLM_BASE_URL"] = BASE
    os.environ["ALOUD_LLM_API_KEY"] = "k"
    os.environ["ALOUD_LLM_MODEL"] = "configured-vision"
    try:
        c = captioner_from_env()
        assert isinstance(c, VisionCaptioner), c
        assert c.base_url == BASE and c.api_key == "k"
        assert c.model == "configured-vision"
    finally:
        for k in ("ALOUD_LLM_BASE_URL", "ALOUD_LLM_API_KEY", "ALOUD_LLM_MODEL"):
            os.environ.pop(k, None)
    print("PASS a configured endpoint is picked up from the environment")


def test_the_request_is_addressed_and_authenticated_correctly():
    """An OpenAI-compatible endpoint answers on /chat/completions and wants a
    bearer token. The stub here answers any POST, which is exactly why neither
    was verified."""
    if not make_frame():
        print("SKIP no ffmpeg"); return
    cap()(FRAME, 10)
    assert STATE["path"] == "/chat/completions", STATE["path"]
    assert STATE["headers"]["Authorization"] == "Bearer k", STATE["headers"]
    assert STATE["req"]["model"] == "stub-vision", STATE["req"].get("model")

    # An operator pastes a base URL with a trailing slash sooner or later, and
    # "//chat/completions" is a 404 on some gateways and a redirect that drops
    # the Authorization header on others.
    VisionCaptioner(base_url=BASE + "/", api_key="k", model="stub-vision")(FRAME, 10)
    assert STATE["path"] == "/chat/completions", STATE["path"]
    print("PASS the request goes to the right path with the right credentials")


def test_the_two_messages_are_labelled_system_and_user():
    """A model reads the roles. The conventions go in the system message and the
    frame in the user message, and swapping or blanking the labels turns the
    rules into something the model can argue with."""
    if not make_frame():
        print("SKIP no ffmpeg"); return
    cap()(FRAME, 10)
    msgs = STATE["req"]["messages"]
    assert [m["role"] for m in msgs] == ["system", "user"], msgs
    text = next(c for c in msgs[1]["content"] if c["type"] == "text")["text"]
    assert "Describe this frame" in text, text
    print("PASS the system and user messages are labelled and instructed")


def test_the_request_asks_for_one_plain_sentence():
    """Description is not a creative writing task: the same frame should give
    the same sentence. And the reply has to have room to finish, because a
    sentence cut off by a token limit is the dangling fragment this project
    refuses to speak."""
    if not make_frame():
        print("SKIP no ffmpeg"); return
    cap()(FRAME, 10)
    assert 0 <= STATE["req"]["temperature"] <= 0.5, STATE["req"]["temperature"]
    assert STATE["req"]["max_tokens"] >= 40, STATE["req"]["max_tokens"]
    print("PASS a low temperature and room for a whole sentence")


def test_a_word_target_below_two_is_raised_to_two():
    """A gap can round down to nothing. Asking a model for zero words gets
    something, and whatever it is was not budgeted for."""
    if not make_frame():
        print("SKIP no ffmpeg"); return
    for asked in (0, 1, -5):
        cap()(FRAME, asked)
        text = next(c for c in STATE["req"]["messages"][1]["content"]
                    if c["type"] == "text")["text"]
        assert "about 2 words" in text, (asked, text)
    print("PASS a word target below two is raised to two")


def test_the_image_is_labelled_with_its_real_type():
    """The mime type comes from the file, not from a guess. A PNG announced as
    a JPEG is rejected by some endpoints and silently misread by others."""
    if not make_frame(PNG_FRAME):
        print("SKIP no ffmpeg"); return
    cap()(PNG_FRAME, 10)
    url = next(c for c in STATE["req"]["messages"][1]["content"]
               if c["type"] == "image_url")["image_url"]["url"]
    assert url.startswith("data:image/png;base64,"), url[:40]
    print("PASS a PNG frame is labelled as a PNG")


def test_every_preamble_in_the_list_is_actually_stripped():
    """Each entry is there because a model produced it. An entry that no longer
    works is a description that starts by describing itself, and it spends the
    gap on words the listener did not need."""
    for prefix in ("Description:", "Audio description:", "The image shows",
                   "This image shows", "The frame shows", "In this frame,",
                   "The scene shows"):
        assert clean(f"{prefix} a man crosses the street") == \
            "A man crosses the street.", prefix
    assert clean("'She opens the door.'") == "She opens the door."
    assert clean("Does he leave?") == "Does he leave?", (
        "a question was given a second terminator")
    print("PASS every preamble in the list is stripped")


# --- the provider abstraction ----------------------------------------------

def test_gemini_is_asked_in_its_own_shape_with_the_same_brief():
    """Same conventions, same word target, same cleaning; only the envelope
    differs. The key goes in a header, never the URL, because URLs are logged."""
    if not make_frame():
        print("SKIP no ffmpeg"); return
    g = GeminiCaptioner(api_key="gk", model="gemini-test", base_url=BASE)
    STATE["reply"] = "The image shows a woman at a window"
    try:
        out = g(FRAME, 9)
    finally:
        STATE["reply"] = "A man crosses the empty street."
    assert out == "A woman at a window.", out
    assert STATE["path"] == "/models/gemini-test:generateContent", STATE["path"]
    assert "gk" not in STATE["path"]
    assert STATE["headers"]["x-goog-api-key"] == "gk", STATE["headers"]
    req = STATE["req"]
    sysmsg = req["systemInstruction"]["parts"][0]["text"].lower()
    assert "present tense" in sysmsg and "name characters" in sysmsg, sysmsg
    parts = req["contents"][0]["parts"]
    assert "about 9 words" in parts[0]["text"], parts[0]
    img = parts[1]["inline_data"]
    assert img["mime_type"] == "image/jpeg" and len(base64.b64decode(img["data"])) > 100
    assert req["generationConfig"]["temperature"] <= 0.5
    print("PASS Gemini gets the same brief in its own request shape")


def test_a_gemini_reply_with_no_text_is_an_error_not_a_blank_cue():
    if not make_frame():
        print("SKIP no ffmpeg"); return
    g = GeminiCaptioner(api_key="gk", model="gemini-test", base_url=BASE)
    STATE["reply"] = ""
    try:
        g(FRAME, 9)
        raise AssertionError("an empty reply was returned as a description")
    except RuntimeError:
        pass
    finally:
        STATE["reply"] = "A man crosses the empty street."
    print("PASS an empty Gemini reply raises")


def test_the_local_model_needs_no_key_but_does_need_a_server():
    clear_provider_env()
    assert not LocalCaptioner().available
    assert LocalCaptioner(base_url=BASE).available
    os.environ["ALOUD_LOCAL_VLM_URL"] = BASE
    try:
        c = captioner_from_env()
        assert isinstance(c, LocalCaptioner), c
        assert "llama.cpp" in c.label, c.label
    finally:
        clear_provider_env()
    print("PASS a local llama.cpp server is a describer with no key")


def test_hosted_beats_local_and_the_choice_can_be_forced():
    """A key added later has to win without anyone remembering to unset the
    local server, and an explicit choice has to be obeyed or refused, never
    quietly swapped for something else."""
    clear_provider_env()
    os.environ["ALOUD_LOCAL_VLM_URL"] = BASE
    os.environ["GEMINI_API_KEY"] = "gk"
    try:
        assert isinstance(captioner_from_env(), GeminiCaptioner)
        os.environ["ALOUD_VISION"] = "local"
        assert isinstance(captioner_from_env(), LocalCaptioner)
        os.environ["ALOUD_VISION"] = "openai"
        try:
            captioner_from_env()
            raise AssertionError("an unconfigured forced provider was accepted")
        except RuntimeError:
            pass
        os.environ["ALOUD_VISION"] = "stub"
        assert not hasattr(captioner_from_env(), "provider")
    finally:
        clear_provider_env()
    print("PASS hosted wins over local, and ALOUD_VISION is obeyed or refused")


def test_more_frames_and_what_was_said_reach_the_model():
    if not make_frame():
        print("SKIP no ffmpeg"); return
    cap()(FRAME, 8, frames=[FRAME], context="A grey-haired man stands at a door.")
    msgs = STATE["req"]["messages"]
    images = [c for c in msgs[1]["content"] if c["type"] == "image_url"]
    assert len(images) == 2, len(images)
    text = next(c for c in msgs[1]["content"] if c["type"] == "text")["text"]
    assert "grey-haired man" in text, text
    sysmsg = msgs[0]["content"]
    assert "same shot" in sysmsg and "Do not repeat" in sysmsg, sysmsg
    print("PASS extra frames and the earlier descriptions are sent")


def test_a_second_sentence_is_dropped():
    assert clean("A man runs. He stops at the door.") == "A man runs."
    assert clean("Mr. Smith waits") == "Mr. Smith waits."
    print("PASS one sentence was asked for and one is kept")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    try:
        for fn in fns:
            fn()
        print(f"\nall green ({len(fns)} tests)")
    finally:
        SRV.shutdown()
