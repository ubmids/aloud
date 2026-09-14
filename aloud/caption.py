"""Describing the frame.

Audio description has conventions, and they are not stylistic preferences. They
come from the fact that the listener is getting this *instead of* seeing it,
while the film carries on around them.

  - Present tense. It is happening now, not in a report afterwards.
  - Say what is visible, not what it means. "She looks at the door" and not
    "she is afraid", because interpreting for the listener takes the film away
    from them and hands back your opinion of it.
  - Never describe what can be heard. The listener already has the audio, and
    spending a gap on "a door slams" spends it on nothing.
  - No character names until the film has given them. A describer who knows the
    script leaks it.
  - New information first. The word budget usually runs out, and what is left
    unsaid should be the least important thing, not the last thing.

The word target is not advice. It comes from the measured length of the gap, and
a description that overruns gets cut or dropped entirely, so hitting it is the
difference between being heard and being silent.
"""
import base64
import json
import mimetypes
import os

SYSTEM = (
    "You write audio description for blind and low vision viewers, spoken aloud "
    "in the gaps between dialogue while the film continues. Describe only what "
    "is visible in this frame. Use the present tense. Do not interpret, "
    "explain, or name emotions. Do not describe anything that can be heard. Do "
    "not name characters. Put the most important new information first, because "
    "the description may be cut short. Write one sentence and no more. Reply "
    "with the sentence alone, no preamble and no quotation marks."
)


def _data_url(path: str) -> str:
    mime = mimetypes.guess_type(path)[0] or "image/jpeg"
    with open(path, "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def clean(text: str) -> str:
    """Strip what models add anyway despite being asked not to."""
    t = (text or "").strip().strip('"').strip("'").strip()
    for prefix in ("Description:", "Audio description:", "The image shows",
                   "This image shows", "The frame shows", "In this frame,",
                   "The scene shows"):
        if t.lower().startswith(prefix.lower()):
            t = t[len(prefix):].lstrip(" ,:")
    if t and not t.endswith((".", "!", "?")):
        t += "."
    return (t[:1].upper() + t[1:]) if t else ""


class VisionCaptioner:
    """A describer backed by any OpenAI-compatible vision endpoint.

    Callable as `captioner(frame_path, target_words)`, which is the contract the
    pipeline expects, so it drops in where the stub was with nothing else
    changing.
    """

    def __init__(self, base_url=None, api_key=None, model=None, timeout=30.0):
        self.base_url = base_url or os.getenv("ALOUD_LLM_BASE_URL")
        self.api_key = api_key or os.getenv("ALOUD_LLM_API_KEY")
        self.model = model or os.getenv("ALOUD_LLM_MODEL", "gpt-4o-mini")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    def __call__(self, frame_path: str, target_words: int) -> str:
        if not self.available:
            raise RuntimeError("no vision endpoint configured")
        import httpx

        n = max(2, int(target_words))
        r = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0.2,
                "max_tokens": 120,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": [
                        {"type": "text", "text":
                            f"Describe this frame in about {n} words. "
                            f"Hitting that length matters: the gap it has to fit "
                            f"in is fixed, and a longer sentence will be cut."},
                        {"type": "image_url",
                         "image_url": {"url": _data_url(frame_path)}},
                    ]},
                ],
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return clean(r.json()["choices"][0]["message"]["content"])


def captioner_from_env(fallback=None):
    """The real describer if one is configured, otherwise the fallback.

    The pipeline must run with no key so that everything around the describer
    stays testable. What it must not do is quietly invent descriptions and let a
    missing key look like a working system, which is why the fallback is the
    obviously-not-looking stub rather than something plausible.
    """
    v = VisionCaptioner()
    if v.available:
        return v
    if fallback is None:
        from .pipeline import stub_captioner
        fallback = stub_captioner
    return fallback
