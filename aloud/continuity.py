"""A continuity pass over a finished track. Off unless asked for.

The describer sees one gap at a time and the last three things it said, so a
whole film comes back with "a grey-haired man" here, "an elderly person"
there, "Young man stands before giant mechanical construct." with no
article, and the same robot introduced three ways. A person reviewing a
track fixes exactly this, and it needs no picture: the whole cue list, the
dialogue and the cast are enough.

So this pass hands a text model all three and asks for each cue back,
rewritten only for consistency: the same name or words for the same person
or thing, articles, present tense. It may not add anything the cue did not
already say. Then every revision is held to the same rules as the first
draft, and kept only if it passes all of them:

  - the sentence gate (`caption.unfit`): finished, and about the picture;
  - no name the cue did not already use, unless the cast list gives it;
  - re-spoken and re-measured, and still inside the cue's own gap.

Anything that fails keeps the original sentence. The original is kept on
the cue as `draft` either way, and the track records which model revised
it, so a reviewer can see what changed and who changed it.

    ALOUD_CONTINUITY=1        turn it on for `describe_film` and `films build`

The text model is chosen the same way as the describer (a Gemini key, then
an OpenAI-compatible endpoint, then a local llama.cpp server); see
docs/DESCRIBERS.md.
"""
import json
import os
import re

BRIEF = (
    "You are revising an audio description track for blind and low vision "
    "viewers. You get every description in order, with its time, the film's "
    "dialogue, and its cast list. Rewrite each description only to make the "
    "track consistent: call the same person or thing by the same name or "
    "words every time, use a name from the cast list once you can tell who it "
    "is, add missing articles, keep the present tense. Do not add any action, "
    "object or detail the description does not already contain. Do not use "
    "more words than the original, beyond a missing article. Do not name anyone who is not in the cast "
    "list. Do not mention the camera, the shot, or the credits. Reply with "
    "JSON only: a list of objects {\"n\": number, \"text\": sentence}, one per "
    "description, in the same order."
)

ON = ("1", "on", "true", "yes")


def enabled() -> bool:
    return (os.getenv("ALOUD_CONTINUITY") or "").strip().lower() in ON


def cast_names(cast: str | None) -> set:
    """The names a cast list gives, as in "Thom: ... The Captain: ..."."""
    names = set()
    for m in re.finditer(r"(?:^|[.;]\s+)(?:The\s+)?([A-Z][\w']*(?:\s[A-Z][\w']*)?):",
                         cast or ""):
        if m.group(1) not in _HEADINGS:
            names.add(m.group(1))
    return names


# Cast lists also carry notes that are not people ("Machines: a flying ship
# ..."), written the same way.
_HEADINGS = {"Machines", "Places", "Others", "Note"}


# Capitalised words that are not names.
_NOT_NAMES = {"On", "I", "A", "An", "The", "Two", "Three", "Four", "His",
              "Her", "Their", "Its", "One", "Some", "Another"}


def _names(text: str) -> set:
    """Capitalised words, other than in quoted screen text, which is the
    film's own words."""
    if re.match(r"on screen:", text or "", re.IGNORECASE):
        return set()
    words = re.findall(r"[A-Za-z][\w']*", text or "")
    # The first word counts too ("Gandalf reads..."), so a revision that
    # opens on a new capitalised word is refused even when it is not a name:
    # keeping the original is the safe side to be wrong on.
    return {w.removesuffix("'s") for w in words
            if w[0].isupper() and w not in _NOT_NAMES}


def new_names(original: str, revised: str, allowed: set) -> set:
    """Names the revision introduces that neither the cue nor the cast had."""
    return _names(revised) - _names(original) - _names(" ".join(allowed)) - allowed


def _words(text: str) -> int:
    return len(re.findall(r"[\w']+", text or ""))


def prompt(cues, dialogue=(), cast: str | None = None) -> str:
    parts = []
    if cast:
        parts.append("Cast: " + cast.strip())
    if dialogue:
        parts.append("Dialogue:\n" + "\n".join(
            f"{a:7.1f}s  {w}" for a, _, w in dialogue))
    parts.append("Descriptions:\n" + "\n".join(
        f"{i}. [{c.start:.1f}s, at most {_words(c.text)} words plus articles] {c.text}"
        for i, c in enumerate(cues, 1)))
    return "\n\n".join(parts)


def parse(reply: str, count: int) -> dict:
    """{cue number: revised text} from the model's JSON, tolerating a fence."""
    t = (reply or "").strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        items = json.loads(t)
    except ValueError:
        m = re.search(r"\[.*\]", t, re.DOTALL)
        if not m:
            return {}
        try:
            items = json.loads(m.group(0))
        except ValueError:
            return {}
    out = {}
    for it in items if isinstance(items, list) else []:
        if isinstance(it, dict) and isinstance(it.get("text"), str):
            try:
                n = int(it.get("n"))
            except (TypeError, ValueError):
                continue
            if 1 <= n <= count:
                out[n] = it["text"]
    return out


def revise(track, *, rewriter, synth, cast: str | None = None,
           dialogue=(), out_dir: str | None = None) -> list:
    """Revise `track` in place. Returns one (cue, outcome) per cue, where the
    outcome is "revised", "unchanged", or why the revision was refused."""
    from .caption import clean, unfit

    cues = track.cues
    if not cues:
        return []
    proposed = parse(rewriter(BRIEF, prompt(cues, dialogue, cast)), len(cues))
    allowed = cast_names(cast)
    log = []
    for i, c in enumerate(cues, 1):
        new = clean(proposed.get(i, ""))
        if not new or new == c.text:
            log.append((c, "unchanged"))
            continue
        why = unfit(new)
        if not why and new_names(c.text, new, allowed):
            why = "it names someone the cast list does not"
        if not why and _words(new) > _words(c.text) + 2:
            why = "it is longer than the original"
        if not why:
            spoken = synth.speak(new, out_dir=out_dir)
            closes = c.gap[1] if c.gap else c.end
            if c.start + spoken.seconds > closes + 0.01:
                why = "it no longer fits its gap"
        if why:
            log.append((c, why))
            continue
        c.draft = c.text
        c.text, c.audio = new, spoken.path
        c.end = round(c.start + spoken.seconds, 3)
        log.append((c, "revised"))
    track.revised_by = getattr(rewriter, "label", "a text model")
    return log


class TextRewriter:
    """The pass's model, over any OpenAI-compatible chat endpoint (a hosted
    one, or llama.cpp's `llama-server` on this machine)."""

    def __init__(self, base_url=None, api_key=None, model=None, timeout=600.0):
        local = os.getenv("ALOUD_LOCAL_VLM_URL")
        self.base_url = base_url or os.getenv("ALOUD_LLM_BASE_URL") or local
        self.api_key = api_key or os.getenv("ALOUD_LLM_API_KEY") or (
            "local" if local else None)
        self.model = model or os.getenv("ALOUD_LLM_MODEL") or os.getenv(
            "ALOUD_LOCAL_VLM_MODEL", "qwen3-vl-4b")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    @property
    def label(self) -> str:
        return f"{self.model} (continuity pass)"

    def __call__(self, system: str, user: str) -> str:
        import httpx
        r = httpx.post(
            f"{self.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model, "temperature": 0.1, "max_tokens": 6000,
                  "messages": [{"role": "system", "content": system},
                               {"role": "user", "content": user}]},
            timeout=self.timeout)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


class GeminiRewriter:
    BASE = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key=None, model=None, base_url=None, timeout=120.0):
        self.api_key = (api_key or os.getenv("GEMINI_API_KEY")
                        or os.getenv("ALOUD_GEMINI_API_KEY"))
        self.model = model or os.getenv("ALOUD_GEMINI_MODEL", "gemini-2.5-flash")
        self.base_url = base_url or os.getenv("ALOUD_GEMINI_BASE_URL", self.BASE)
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    @property
    def label(self) -> str:
        return f"{self.model} (continuity pass)"

    def __call__(self, system: str, user: str) -> str:
        import httpx
        config = {"temperature": 0.1, "maxOutputTokens": 8000,
                  "responseMimeType": "application/json"}
        if self.model.startswith("gemini-2.5"):
            config["thinkingConfig"] = {"thinkingBudget": 0}
        r = httpx.post(
            f"{self.base_url.rstrip('/')}/models/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            json={"systemInstruction": {"parts": [{"text": system}]},
                  "contents": [{"role": "user", "parts": [{"text": user}]}],
                  "generationConfig": config},
            timeout=self.timeout)
        r.raise_for_status()
        cand = (r.json().get("candidates") or [{}])[0]
        return "".join(p.get("text", "")
                       for p in cand.get("content", {}).get("parts", []))


def rewriter_from_env():
    """The same order as the describer: Gemini, then an OpenAI-compatible or
    local endpoint. None if nothing is configured."""
    for make in (GeminiRewriter, TextRewriter):
        r = make()
        if r.available:
            return r
    return None
