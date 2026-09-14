"""The vision describer, against a stub that speaks its protocol.

Same reasoning as Hearth's extraction tests: without a key this path would ship
never having executed, and the request shape, the image encoding and the
response cleaning would all be unverified.
"""
import base64
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.caption import VisionCaptioner, captioner_from_env, clean

STATE = {"reply": "A man crosses the empty street.", "status": 200, "req": None}
FRAME = "/tmp/aloud_caption_frame.jpg"


class Stub(BaseHTTPRequestHandler):
    def do_POST(self):
        STATE["req"] = json.loads(self.rfile.read(
            int(self.headers.get("Content-Length", 0))))
        if STATE["status"] != 200:
            self.send_response(STATE["status"]); self.end_headers()
            self.wfile.write(b'{"error":"nope"}'); return
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


def make_frame():
    import subprocess, shutil
    if os.path.exists(FRAME):
        return True
    if not shutil.which("ffmpeg"):
        return False
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
                    "-i", "color=c=navy:s=160x90:d=1", "-frames:v", "1", FRAME],
                   check=True)
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
    for k in ("ALOUD_LLM_BASE_URL", "ALOUD_LLM_API_KEY"):
        os.environ.pop(k, None)
    c = captioner_from_env()
    assert not isinstance(c, VisionCaptioner)
    out = c("/nonexistent.jpg", 8)
    assert "scene changes" in out, out
    print("PASS with no endpoint the obvious stub is used, not a plausible fake")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    try:
        for fn in fns:
            fn()
        print(f"\nall green ({len(fns)} tests)")
    finally:
        SRV.shutdown()
