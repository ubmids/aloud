"""The title's own caption file, read as a map of where people are talking.

Every film on a streaming service already carries one. Captions are written by
someone who listened to every line, so they know about the line shouted over an
explosion that no detector can hear, and they cost nothing to read. Aloud uses
them as a second, independent dialogue map: a gap has to be silent to the ear
AND clear of every caption.

Caption timing is loose. Cues are rounded, held on screen after the line ends
for reading time, and sometimes appear a beat late. Holding on too long only
shrinks a gap, which is safe. Appearing late is not, so every cue is widened at
the front by more than at the back.
"""
import re

_TIME = r"(?:(\d+):)?(\d{1,2}):(\d{2})[,.](\d{1,3})"
_CUE = re.compile(_TIME + r"\s*-->\s*" + _TIME)


def _seconds(h, m, s, ms) -> float:
    return int(h or 0) * 3600 + int(m) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def parse(text: str) -> list[tuple[float, float]]:
    """(start, end) for every cue in an SRT or WebVTT file, in order."""
    spans = []
    for m in _CUE.finditer(text or ""):
        g = m.groups()
        a, b = _seconds(*g[:4]), _seconds(*g[4:])
        if b > a:
            spans.append((a, b))
    return sorted(spans)


def speech_spans(path: str, *, lead: float = 0.4,
                 tail: float = 0.25) -> list[tuple[float, float]]:
    """The caption cues in `path`, widened to cover the line they caption."""
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        spans = parse(f.read())
    return [(max(0.0, a - lead), b + tail) for a, b in spans]


def lines(path: str) -> list[tuple[float, float, str]]:
    """(start, end, words) for every caption, for a pass that reads the
    dialogue as well as its timing (see continuity.py)."""
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        text = f.read()
    out = []
    for block in re.split(r"\n\s*\n", text.replace("\r", "")):
        m = _CUE.search(block)
        if not m:
            continue
        g = m.groups()
        words = " ".join(l.strip() for l in block[m.end():].splitlines()
                         if l.strip())
        out.append((_seconds(*g[:4]), _seconds(*g[4:]), words))
    return sorted(out)
