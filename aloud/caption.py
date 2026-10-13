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

Three describers, one contract, chosen by the environment (see
`captioner_from_env`):

  - any OpenAI-compatible vision endpoint (`ALOUD_LLM_*`)
  - Google Gemini (`GEMINI_API_KEY`)
  - a local open model on the CPU, served by llama.cpp's `llama-server`, which
    speaks the same OpenAI protocol (`ALOUD_LOCAL_VLM_URL`). The tracks in the
    app were written this way, by Qwen3-VL 8B on a CPU, so they are real
    descriptions of real frames with no key and no GPU. Regenerating them with
    a hosted model is one environment variable and the same command.

The word target is not advice. It comes from the measured length of the gap, and
a description that overruns gets cut or dropped entirely, so hitting it is the
difference between being heard and being silent.
"""
import base64
import json
import mimetypes
import os
import re

SYSTEM = (
    "You write audio description for blind and low vision viewers, spoken aloud "
    "in the gaps between dialogue while the film continues. Describe only what "
    "is visible in this frame. Use the present tense. Do not interpret, "
    "explain, or name emotions. Do not describe anything that can be heard. Do "
    "not name characters. Put the most important new information first, because "
    "the description may be cut short. Describe people by what can be seen "
    "of them: age, hair, clothing. If there is legible text on screen and it "
    "fits the length, read it out exactly; otherwise describe the picture. "
    "Never say only that text appears or that the scene changes. Write one "
    "sentence and no more. Reply "
    "with the sentence alone, no preamble and no quotation marks."
)

# Added when the describer is shown more than one frame of the same shot. A
# single still cannot tell "she raises the gun" from "she holds a gun", and the
# action is usually the thing worth the gap.
MOTION = (
    " You are shown frames from the same shot, in order. If something moves or "
    "changes between them, describe the action rather than the still picture."
)

# Added when the describer knows what has already been said. Without it every
# cue starts from nothing: "A man in a jacket..." four times in a minute, about
# the same man, which is the listener's time spent on something they already
# know.
CONTEXT = (
    " The listener has already heard the descriptions given below. Do not "
    "repeat them; say what is new. Refer back to people already described by "
    "what was said about them, for example 'the grey-haired man'."
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
    # One sentence was asked for. A model that writes two has spent the
    # budget's measurement on a sentence the fitting loop will then have to
    # throw away whole, so the second goes now.
    m = re.search(r"(?<!\bMr)(?<!\bMrs)(?<!\bMs)(?<!\bDr)(?<!\bSt)[.!?]\s+(?=\S)", t)
    if m:
        t = t[:m.start() + 1]
    if t and not t.endswith((".", "!", "?")):
        t += "."
    return (t[:1].upper() + t[1:]) if t else ""


# Sentences that are about the film rather than of it. Each one here was
# produced by a real model on a real frame, and each one spends a gap telling
# the listener nothing: "Text appears on screen." while the screen read "This
# film is supported by the Netherlands Film Fund". Better silent.
VACUOUS = re.compile(
    r"^(?:the )?(?:text|words|a title|credits|captions?|subtitles?|an? image|"
    r"the image|the scene|the screen|the frame|a scene|it)\s+"
    r"(?:appears?|is shown|is displayed|are displayed|are shown|changes?|cuts?|"
    r"fades?|shows?|is black|goes black|is dark)\b[^.]*\.?$|^(?:the )?screen is "
    r"(?:completely )?(?:black|dark)\b", re.IGNORECASE)


def vacuous(text: str) -> bool:
    """True for a description that only says the film is a film."""
    return bool(VACUOUS.search((text or "").strip()))


def brief_version() -> str:
    """Changes whenever the brief does, so remembered answers to an older
    brief are not reused for a newer one."""
    import hashlib
    return hashlib.sha256((SYSTEM + MOTION + CONTEXT).encode()).hexdigest()[:8]


def _ask(n: int, frames: int, context: str | None) -> tuple[str, str]:
    """The system and user text for one request, shared by every provider so
    that switching describers changes the model and nothing about the brief."""
    system = SYSTEM + (MOTION if frames > 1 else "") + (CONTEXT if context else "")
    user = (f"Describe this frame in about {n} words. "
            f"Hitting that length matters: the gap it has to fit "
            f"in is fixed, and a longer sentence will be cut.")
    if context:
        user += "\n\nAlready described, most recent last:\n" + context
    return system, user


class VisionCaptioner:
    """A describer backed by any OpenAI-compatible vision endpoint.

    Callable as `captioner(frame_path, target_words)`, which is the contract the
    pipeline expects, so it drops in where the stub was with nothing else
    changing. `frames` (more stills from the same shot) and `context` (what has
    already been said) are optional and make the descriptions better; the
    pipeline passes them to any describer that sets `takes_context`.
    """

    provider = "openai-compatible"
    takes_context = True

    def __init__(self, base_url=None, api_key=None, model=None, timeout=30.0):
        self.base_url = base_url or os.getenv("ALOUD_LLM_BASE_URL")
        self.api_key = api_key or os.getenv("ALOUD_LLM_API_KEY")
        self.model = model or os.getenv("ALOUD_LLM_MODEL", "gpt-4o-mini")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    @property
    def label(self) -> str:
        """Who wrote the descriptions, for the track's provenance."""
        return f"{self.model} ({self.provider})"

    def __call__(self, frame_path: str, target_words: int, *,
                 frames=(), context: str | None = None) -> str:
        if not self.available:
            raise RuntimeError("no vision endpoint configured")
        import httpx

        n = max(2, int(target_words))
        stills = [frame_path, *frames]
        system, user = _ask(n, len(stills), context)
        r = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0.2,
                "max_tokens": 120,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": [
                        {"type": "text", "text": user},
                        *({"type": "image_url",
                           "image_url": {"url": _data_url(p)}} for p in stills),
                    ]},
                ],
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        return clean(r.json()["choices"][0]["message"]["content"])


class LocalCaptioner(VisionCaptioner):
    """An open vision model on this machine's CPU, through llama.cpp.

    `llama-server` speaks the OpenAI protocol, so this is the same describer
    pointed at localhost with no key. It exists as its own class so that "no
    key" is a deliberate, named configuration rather than a hole in the check
    that a hosted endpoint needs one. See docs/DESCRIBERS.md for the command
    that starts the server.
    """

    provider = "local, llama.cpp on CPU"

    def __init__(self, base_url=None, model=None, timeout=600.0):
        super().__init__(
            base_url=base_url or os.getenv("ALOUD_LOCAL_VLM_URL"),
            api_key="local",
            model=model or os.getenv("ALOUD_LOCAL_VLM_MODEL", "qwen3-vl-8b"),
            timeout=timeout)


class GeminiCaptioner:
    """Google Gemini, through the Generative Language REST API.

    Same brief, same cleaning, same contract as the OpenAI-compatible path.
    The request differs only in shape: the system prompt is a
    `systemInstruction`, images are `inline_data`, and the key travels in the
    `x-goog-api-key` header rather than the URL, where it would end up in logs.
    """

    provider = "Google Gemini"
    takes_context = True
    BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key=None, model=None, base_url=None, timeout=60.0):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY")
                        or os.getenv("ALOUD_GEMINI_API_KEY"))
        self.model = model or os.getenv("ALOUD_GEMINI_MODEL", "gemini-2.5-flash")
        self.base_url = base_url or os.getenv("ALOUD_GEMINI_BASE_URL", self.BASE)
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key and self.base_url)

    @property
    def label(self) -> str:
        return f"{self.model} ({self.provider})"

    def __call__(self, frame_path: str, target_words: int, *,
                 frames=(), context: str | None = None) -> str:
        if not self.available:
            raise RuntimeError("no Gemini key configured")
        import httpx

        n = max(2, int(target_words))
        stills = [frame_path, *frames]
        system, user = _ask(n, len(stills), context)
        parts = [{"text": user}]
        for p in stills:
            url = _data_url(p)
            mime, data = url[5:].split(";base64,", 1)
            parts.append({"inline_data": {"mime_type": mime, "data": data}})
        config = {"temperature": 0.2, "maxOutputTokens": 200}
        # 2.5 models think by default, and the thinking is charged against the
        # same output limit: a one-sentence answer can come back empty because
        # the model spent its tokens deciding what to say. A frame description
        # does not need it.
        if self.model.startswith("gemini-2.5"):
            config["thinkingConfig"] = {"thinkingBudget": 0}
        r = httpx.post(
            f"{self.base_url.rstrip('/')}/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": parts}],
                "generationConfig": config,
            },
            timeout=self.timeout,
        )
        r.raise_for_status()
        cand = (r.json().get("candidates") or [{}])[0]
        text = "".join(p.get("text", "")
                       for p in cand.get("content", {}).get("parts", []))
        if not text.strip():
            raise RuntimeError(
                f"Gemini returned no text ({cand.get('finishReason', 'unknown')})")
        return clean(text)


PROVIDERS = {
    "gemini": GeminiCaptioner,
    "openai": VisionCaptioner,
    "local": LocalCaptioner,
}


def captioner_from_env(fallback=None):
    """The real describer if one is configured, otherwise the fallback.

    `ALOUD_VISION=gemini|openai|local|stub` chooses outright. Without it the
    first one configured wins, hosted before local: a Gemini key, then an
    OpenAI-compatible endpoint, then a local llama.cpp server.

    The pipeline must run with no key so that everything around the describer
    stays testable. What it must not do is quietly invent descriptions and let a
    missing key look like a working system, which is why the fallback is the
    obviously-not-looking stub rather than something plausible.
    """
    if fallback is None:
        from .pipeline import stub_captioner
        fallback = stub_captioner

    chosen = (os.getenv("ALOUD_VISION") or "").strip().lower()
    if chosen == "stub":
        return fallback
    if chosen:
        if chosen not in PROVIDERS:
            raise ValueError(f"ALOUD_VISION={chosen!r}: expected one of "
                             f"{', '.join(PROVIDERS)} or stub")
        c = PROVIDERS[chosen]()
        if not c.available:
            raise RuntimeError(f"ALOUD_VISION={chosen} but it is not configured")
        return c

    for make in (GeminiCaptioner, VisionCaptioner, LocalCaptioner):
        c = make()
        if c.available:
            return c
    return fallback
