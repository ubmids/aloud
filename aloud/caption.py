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
    app were written this way, by Qwen3-VL 4B on a CPU, so they are real
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
    "the description may be cut short. Say first who is in the shot and "
    "where, then what they are doing. Describe people by what can be seen "
    "of them: age, hair, clothing. Skip small details of faces, eyes and "
    "hands unless they are the main action. If there is legible text on screen and it "
    "fits the length, say 'On screen:' and then the words exactly; otherwise "
    "describe the picture. "
    "Never say only that text appears or that the scene changes. Describe "
    "the world of the film as if it were real: never mention the camera, "
    "shots, framing or close-ups, never say it is animated or a cartoon, "
    "never mention logos or credits, and never compare with an earlier moment "
    "('previously', 'now'). Write one "
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
    "repeat them; say what is new. Refer back to anyone already described "
    "by the words already used for them, rather than describing them afresh."
)


# Replaces "Do not name characters." when the title has a cast. Audio
# description names a character once the film has, and a listener who hears
# "the red-haired figure" thirty times in Sintel is being told less than the
# film tells a sighted viewer. The list is the only source of names, so the
# model is never invited to guess one.
NO_NAMES = "Do not name characters. "
CAST = (
    " This film's characters, as the film itself names them: {cast} When "
    "you recognise one of them, call them by that name. Use only the names in "
    "this cast list; describe anyone else by what can be seen of them."
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
    # Every creature in an animated film is "animated" or "a cartoon" to a
    # vision model. The creature is worth the gap; the word is about the film,
    # and dropping it keeps a sentence that would otherwise be refused whole.
    if not re.match(r"on screen:", t, re.IGNORECASE):
        t = re.sub(r"\b(?:animated|cartoon|cgi|computer-generated)\s+(?=[A-Za-z])",
                   "", t, flags=re.IGNORECASE)
        t = re.sub(r",\s*,", ",", t)
    if t and not t.endswith((".", "!", "?")):
        t += "."
    return (t[:1].upper() + t[1:]) if t else ""


# Sentences that are about the film rather than of it. Each one here was
# produced by a real model on a real frame, and each one spends a gap telling
# the listener nothing: "Text appears on screen." while the screen read "This
# film is supported by the Netherlands Film Fund". Better silent.
VACUOUS = re.compile(
    r"^(?:the |an? )?(?:[a-z]+ ){0,2}(?:text|words|a title|credits|captions?|subtitles?|an? image|"
    r"the image|the scene|the screen|the frame|a scene|it)\s+"
    r"(?:appears?|is shown|is displayed|are displayed|are shown|changes?|cuts?|"
    r"fades?|shows?|is black|goes black|is dark)\b[^.]*\.?$|^(?:the )?screen is "
    r"(?:completely )?(?:black|dark)\b", re.IGNORECASE)


def vacuous(text: str) -> bool:
    """True for a description that only says the film is a film."""
    return bool(VACUOUS.search((text or "").strip()))


# Sentences that are about the film as a made thing, anywhere in them, not only
# when that is all they say. Each pattern is from a cue that shipped: "The
# Blender Foundation Presents logo appears...", "The camera focuses on...",
# "A close-up of...", "...previously stretching, now...", "...scrolling white
# credit text", "...fills the frame", "...in a fast-moving, low-angle shot".
# The listener is inside the film; a describer pointing at the camera takes
# them out of it, and spends the gap doing it.
META = re.compile(
    r"\blogos?\b|\bthe camera\b|\bcamera (?:pans|focuses|zooms|cuts|moves|tilts|"
    r"tracks|lingers|shows)\b|\bclose-?ups?\b|\bpreviously\b|"
    r"\b(?:white|scrolling|rolling|credit|end)\s+(?:\w+\s+)?text\b|"
    r"\bcredits? (?:roll|scroll|text|appear)|"
    r"\b(?:fills?|enters?|leaves?|exits?|in|out of|of) the frame\b|"
    r"\b(?:angle|tracking|wide|aerial|establishing|long|medium) shot\b|"
    r"\banimated\b|\bcartoon\b|\bcgi\b|\bcomputer-generated\b|"
    # The lens, by another name. "...confronting Sintel whose red hair is
    # blurred", "A blurred foreground post frames a street", "looks
    # off-camera", "hangs in focus against a softly blurred forest": each
    # shipped, and each describes the photography rather than the world.
    r"\bblurr(?:ed|y|ing)\b|\b(?:in|out of|soft) focus\b|\boff-?camera\b|"
    # "rests beside credits on a weathered wooden surface": the brief says
    # never mention credits, and the end-credit artwork is not the story.
    r"\bcredits\b",
    re.IGNORECASE)

# The film's own words may be read out ("On screen: 40 YEARS LATER."), but
# not its crew list. "On screen: Produced by TON ROOSENDAAL." was spoken over
# the closing battle of Tears of Steel, and "On screen: credits list names
# like ..." is not the words on screen at all, but a summary of them.
CREDIT_READING = re.compile(
    r"^on screen:.*(?:\b(?:produced|directed|written|edited|composed|music|"
    r"screenplay|story|executive producer)\b(?:\s+\w+)?\s+by\b|"
    r"\bcredits?\b|\bnames like\b)", re.IGNORECASE)


def meta(text: str) -> bool:
    """True for a sentence about the film rather than in it."""
    t = (text or "").strip()
    if re.match(r"on screen:", t, re.IGNORECASE):
        return False                      # the film's own words, quoted
    return vacuous(t) or bool(META.search(t))


def unfit(text: str) -> str | None:
    """Why a finished sentence must not be spoken, or None if it may be.

    The one gate every cue passes twice: in the pipeline before it is
    synthesised, and in `publish` before it ships inside the app.
    """
    from .budget import dangles
    if dangles(text):
        return "it stops before its noun"
    if meta(text):
        return "it is about the film, not in it"
    if CREDIT_READING.search((text or "").strip()):
        return "it reads out the credits"
    return None


_STOP = {"a", "an", "the", "and", "of", "in", "on", "at", "to", "with", "his",
         "her", "their", "its", "is", "are", "while", "as"}


def _content_words(text: str) -> set:
    words = re.findall(r"[a-z']+", (text or "").lower().replace("\u2019", "'"))
    words = [w[:-2] if w.endswith("'s") else w.strip("'") for w in words]
    return {w for w in words if w not in _STOP and len(w) > 2}


def repeats(text: str, earlier, novelty: float = 0.34) -> bool:
    """True if `text` mostly says what one of `earlier` already said.

    "The man's eyes remain closed." came back thirty seconds after the same
    sentence. The describer is told what it said, and still does this; a
    sentence the listener has already heard is a gap spent on nothing.

    Measured as what is new, not what is shared. The brief tells the
    describer to refer back to people by what was already said of them ("the
    grey-haired man"), so a good next sentence shares its subject with the
    last one by design. The first rule, overlap against the shorter sentence,
    refused "A figure in heavy gear drops the glowing object as debris falls."
    for sharing "figure in heavy gear ... glowing object" with the cue before
    it, and left eighteen gaps of Tears of Steel silent, some of them ten
    seconds long in the middle of a battle. A sentence is a repeat when it
    adds fewer than two content words, or new words are under a third of it.
    """
    mine = _content_words(text)
    if not mine:
        return False
    for e in earlier:
        theirs = _content_words(e)
        if not theirs:
            continue
        new = mine - theirs
        if len(new) < 2 or len(new) / len(mine) < novelty:
            return True
    return False


def ask_version(n: int) -> str:
    """The brief's version as it applies to an ask of `n` words. Short asks
    have their own wording, so their remembered answers are kept apart and a
    change to it re-asks only them."""
    return brief_version() + ("-short2" if n <= SHORT_WORDS else "")


def brief_version() -> str:
    """Changes whenever the brief does, so remembered answers to an older
    brief are not reused for a newer one."""
    import hashlib
    return hashlib.sha256((SYSTEM + MOTION + CONTEXT + CAST).encode()).hexdigest()[:8]


# At or under this many words the ask changes from "about" to "at most", with
# an example. Most of the silent gaps in the first Tears of Steel tracks were
# a second and a half to two and a half seconds long, room for three to five
# words, and a 4B model asked for "about 4 words" wrote eight, then eight
# again. Shown the shape of a short description, it writes one. The examples
# must not come from any film on the shelf: the first ones did ("A clock tower
# shatters." is a Tears of Steel description), and the model began finding
# clock towers in shots that had none.
SHORT_WORDS = 6


def _ask(n: int, frames: int, context: str | None,
         cast: str | None = None) -> tuple[str, str]:
    """The system and user text for one request, shared by every provider so
    that switching describers changes the model and nothing about the brief."""
    system = SYSTEM.replace(NO_NAMES, "") if cast else SYSTEM
    system += (MOTION if frames > 1 else "") + (CONTEXT if context else "")
    if cast:
        system += CAST.format(cast=cast.strip())
    if n <= SHORT_WORDS:
        user = (f"Describe this frame in {n} words or fewer: who or what, and "
                f"what they do, like \"Two men shake hands.\" or \"The "
                f"woman runs.\" The gap is short; a longer sentence will not "
                f"be heard at all.")
    else:
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
                 frames=(), context: str | None = None,
                 cast: str | None = None) -> str:
        if not self.available:
            raise RuntimeError("no vision endpoint configured")
        import httpx

        n = max(2, int(target_words))
        stills = [frame_path, *frames]
        system, user = _ask(n, len(stills), context, cast)
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
            model=model or os.getenv("ALOUD_LOCAL_VLM_MODEL", "qwen3-vl-4b"),
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
                 frames=(), context: str | None = None,
                 cast: str | None = None) -> str:
        if not self.available:
            raise RuntimeError("no Gemini key configured")
        import httpx

        n = max(2, int(target_words))
        stills = [frame_path, *frames]
        system, user = _ask(n, len(stills), context, cast)
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
