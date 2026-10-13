"""Fitting a description into the hole you actually have.

Audio description is not a captioning problem, it is a scheduling problem. The
gap is fixed and the sentence has to fit inside it when *spoken*, which is a
different constraint from fitting in a character count. "17:42" is five
characters and takes about a second to say. "a" is one character and takes a
fifth of that.

So the budget here is measured in seconds of speech, and the estimator that
converts text to seconds is calibrated against a real synthesiser rather than a
guessed words-per-minute constant. `calibrate.py` regenerates the coefficients.
"""
import re
from dataclasses import dataclass

# Calibrated, not guessed. See calibrate.py and CALIBRATION.md for the method
# and the residuals. Duration is modelled as a fixed cost per utterance plus a
# cost per syllable, because a five-word sentence of long words takes longer
# than a five-word sentence of short ones and a words-per-minute model cannot
# see the difference.
FIXED_COST_S = 0.200
SECONDS_PER_SYLLABLE = 0.203
# Commas and full stops buy real pauses; the synthesiser inserts them whether
# the budget accounted for them or not.
PAUSE_COMMA_S = 0.12
PAUSE_STOP_S = 0.28

# Leave the edges of the gap alone. A description that begins the instant the
# previous line ends and finishes as the next begins is technically inside the
# gap and sounds like an interruption.
HEADROOM = 0.85

# Used only when no synthesiser is available and the estimator is all there is.
# Calibration against a real voice left a worst-case residual of 0.62s, so an
# estimate-only fit has to hold that much back or it will confidently schedule a
# cue that overruns. When a synthesiser IS available the pipeline measures the
# real duration and this margin is not applied, because there is nothing left to
# be uncertain about.
ESTIMATE_ERROR_S = 0.62

_VOWELS = "aeiouy"


def syllables(word: str) -> int:
    """Cheap English syllable count. Wrong on individual words, close enough in
    aggregate, and it has no dependencies, which matters more here than being
    right about 'queueing'."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    count, prev_vowel = 0, False
    for ch in w:
        is_vowel = ch in _VOWELS
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if w.endswith("e") and count > 1 and not w.endswith(("le", "ee", "ye")):
        count -= 1
    return max(1, count)


def speech_seconds(text: str) -> float:
    """How long a synthesiser will take to say this."""
    text = (text or "").strip()
    if not text:
        return 0.0
    syl = sum(syllables(w) for w in re.findall(r"[A-Za-z']+", text))
    digits = len(re.findall(r"\d", text))          # spoken one at a time, roughly
    commas = text.count(",") + text.count(";")
    stops = len(re.findall(r"[.!?]", text))
    return (FIXED_COST_S + syl * SECONDS_PER_SYLLABLE
            + digits * SECONDS_PER_SYLLABLE
            + commas * PAUSE_COMMA_S + stops * PAUSE_STOP_S)


def budget_for(gap_seconds: float, headroom: float = HEADROOM) -> float:
    """Seconds of speech a gap of this length can actually carry."""
    return max(0.0, gap_seconds * headroom)


def words_for(gap_seconds: float, headroom: float = HEADROOM) -> int:
    """A word target to hand the describer, so it aims at the right size rather
    than writing whatever it likes and being truncated afterwards."""
    budget = budget_for(gap_seconds, headroom)
    # ~1.45 syllables per word in ordinary descriptive English.
    usable = max(0.0, budget - FIXED_COST_S)
    return max(0, int(usable / (SECONDS_PER_SYLLABLE * 1.45)))


def fit_measured(text: str, gap_seconds: float, synth, *,
                 headroom: float = HEADROOM, max_rounds: int = 6) -> "Fit":
    """Fit by synthesising and measuring, rather than by estimating.

    Trims and re-measures until it genuinely fits. Costs a few synthesiser calls
    per cue, which is nothing next to describing the frames, and removes the
    entire class of bug where a cue was scheduled on a prediction and clipped in
    reality.
    """
    budget = budget_for(gap_seconds, headroom)
    candidate = (text or "").strip()
    trimmed = False

    for _ in range(max_rounds):
        if not candidate:
            break
        actual = synth.duration(candidate)
        if actual <= budget:
            return Fit(candidate, round(actual, 3), round(budget, 3), True, trimmed)
        # Overran. Shorten by the measured overshoot rather than by one word at
        # a time, so a badly oversized description converges in a round or two.
        overshoot = actual - budget
        drop = max(1, int(overshoot / (SECONDS_PER_SYLLABLE * 1.45)))
        shorter = _shorten(candidate, drop)
        if shorter == candidate:
            break
        candidate, trimmed = shorter, True

    return Fit("", 0.0, round(budget, 3), False, True)


# A description must never end on one of these. "A man in a grey." is inside
# its budget and says nothing; the listener is left waiting for a noun that
# never arrives, which is worse than silence because they now believe they
# missed something. Truncation that lands here keeps backing up to the previous
# clean boundary, and gives up rather than emit a dangling phrase.
DANGLING = {
    "a", "an", "the", "and", "or", "but", "as", "of", "in", "on", "at", "to",
    "for", "with", "from", "into", "over", "under", "by", "his", "her", "its",
    "their", "this", "that", "these", "those", "is", "was", "are", "were",
    "then", "while", "when", "who", "which", "very", "more", "two", "three",
}


MIN_CLAUSE_WORDS = 4

# A comma after a word like these is usually between two adjectives, not
# between two clauses. "A massive mechanical structure looms over a misty,
# smoke-filled cityscape." cut at its comma gave "...looms over a misty." on
# Tears of Steel: inside budget, ends on a word that is not in the dangling
# list, and leaves the listener waiting for the noun. There is no tagger here,
# so the test is the word's shape: a list of the adjectives describers reach
# for, and the suffixes adjectives wear. It refuses some honest cuts ("over a
# city,") and that is the right way round: a refused cut is a re-ask or a
# silent gap, a wrong one is a broken sentence read aloud.
MODIFIERS = {
    "large", "small", "big", "huge", "vast", "tall", "short", "long", "wide",
    "narrow", "thick", "thin", "dark", "dim", "bright", "pale", "old", "young",
    "new", "white", "black", "red", "blue", "green", "grey", "gray", "brown",
    "golden", "silver", "orange", "yellow", "purple", "pink", "empty", "distant",
    "broken", "ruined", "wet", "cold", "warm", "hot", "heavy", "light", "deep",
    "high", "low", "open", "closed", "bare", "faint", "sharp", "soft", "hard",
}
# Words ending in -y that are things, not qualities.
_Y_NOUNS = {
    "sky", "city", "body", "factory", "gallery", "balcony", "army", "party",
    "family", "lady", "baby", "story", "ceremony", "laboratory", "territory",
    "debris", "country", "boy", "doorway", "hallway", "alley", "valley",
    "highway", "stairway", "galaxy", "facility", "jetty", "embassy", "agency",
    "enemy", "energy", "memory", "battery", "machinery", "scenery", "academy",
}
_MODIFIER_SUFFIX = re.compile(r"(?:ive|ous|ful|ish|less|ic|[^aeiouy]y)$")


# Words that open a clause or a phrase of its own. A comma before one of these
# is a real boundary whatever came before it: "thick and steady, burying the
# parked cars" can lose its second half even though "steady" is an adjective.
_OPENERS = {
    "with", "while", "as", "and", "but", "which", "who", "whose", "where",
    "its", "his", "her", "their", "each", "both", "one", "then", "now", "near",
    "beside", "behind", "under", "over", "through", "against", "before",
    "after", "surrounded", "dressed", "framed", "lit",
}


# What follows a verb in -ing when it opens a clause: "holding a rifle",
# "running toward the door". An -ing word followed by anything else is usually
# an adjective: "a shattered, glowing window".
_AFTER_VERB = {
    "a", "an", "the", "his", "her", "its", "their", "this", "that", "these",
    "those", "him", "them", "it", "into", "onto", "through", "toward",
    "towards", "across", "along", "past", "over", "under", "up", "down", "out",
    "away", "back", "around", "at", "on", "in", "from", "with", "to", "off",
}
_DETERMINERS = {
    "a", "an", "the", "his", "her", "its", "their", "this", "that", "these",
    "those", "some", "two", "three", "four", "several", "many", "each",
}
# Words ending in -ed or -ing that are things.
_ED_ING_NOUNS = {
    "bed", "shed", "sled", "seed", "reed", "steed", "speed", "feed", "weed",
    "building", "ceiling", "painting", "clearing", "opening", "landing",
    "railing", "wedding", "evening", "morning", "ring", "king", "thing",
    "string", "wing", "spring", "swing", "sibling", "dwelling", "crossing",
    "gathering", "meeting", "recording", "drawing", "clothing", "housing",
    "wiring", "piping", "scaffolding", "plating", "lining", "setting",
    "ending", "lightning", "footing", "sling", "ping", "awning", "carving",
}


def _bare(word: str) -> str:
    return re.sub(r"[^A-Za-z'-]", "", word).lower()


def _opens_clause(piece: str) -> bool:
    words = [_bare(w) for w in piece.split()]
    if not words:
        return False
    first = words[0]
    if first in _OPENERS:
        return True
    return (first.endswith("ing") and "-" not in first and len(words) >= 3
            and words[1] in _AFTER_VERB)


def _ends_on_modifier(words: list[str]) -> bool:
    if not words:
        return False
    last = _bare(words[-1])
    if last in MODIFIERS:
        return True
    if last in _Y_NOUNS or last in _ED_ING_NOUNS:
        return False
    if "-" in last:
        return last.endswith(("ed", "ing", "like"))
    if _MODIFIER_SUFFIX.search(last):
        return True
    # "through a shattered," and "beside a glowing,": a participle straight
    # after a determiner, or after another adjective, is describing a noun
    # that the cut has just removed.
    if last.endswith(("ed", "ing")) and len(words) >= 2:
        before = _bare(words[-2])
        return before in _DETERMINERS or _ends_on_modifier(words[:-1])
    return False


def _ends_cleanly(words: list[str]) -> bool:
    if not words:
        return False
    last = re.sub(r"[^A-Za-z']", "", words[-1]).lower()
    return bool(last) and last not in DANGLING


def _shorten(text: str, words_to_drop: int) -> str:
    """Drop a trailing clause if there is one, otherwise whole words, and never
    stop on a word that leaves the sentence hanging."""
    parts = re.split(r"(?<=[,;])\s+", text.strip())
    if len(parts) > 1:
        shorter = " ".join(parts[:-1]).rstrip(",;")
        words = re.findall(r"\S+", shorter)
        # Not every comma ends a clause. "A large, dark hall looms." cut at
        # its comma gave "A large, dark." on the first full film: inside
        # budget, ends on an ordinary adjective, says nothing. A clause worth
        # keeping has a subject and a verb, so it runs to at least four words,
        # and no piece of it between commas is a lone word, which is what an
        # adjective list looks like.
        pieces = [p for p in re.split(r"[,;]", shorter) if p.strip()]
        if (_ends_cleanly(words) and len(words) >= MIN_CLAUSE_WORDS
                and (_opens_clause(parts[-1]) or not _ends_on_modifier(words))
                and all(len(p.split()) >= 2 for p in pieces)):
            return shorter + "."
        return ""

    # No word-level truncation. Cutting inside a phrase produced things like
    # "A man in a grey." which is inside budget, grammatical enough to pass a
    # function-word check, and says nothing: the listener waits for a noun that
    # never comes and believes they missed it. Chasing that with a longer stop
    # list is whack-a-mole, because the offending word is an ordinary adjective.
    # So the rule is structural instead of lexical: cut at punctuation or not at
    # all, and if nothing fits, say nothing. Silence is a valid description.
    return ""


def fit_generated(describe, gap_seconds: float, synth, *,
                  headroom: float = HEADROOM, max_rounds: int = 4) -> "Fit":
    """Ask for a description the right size, rather than cutting one to size.

    `describe(target_words)` returns a description of roughly that length. This
    is the path the pipeline actually takes: length is a constraint handed to the
    writer, not damage done afterwards. Truncation still exists underneath as a
    guard, but by the time it runs something has already gone wrong.
    """
    budget = budget_for(gap_seconds, headroom)
    target = words_for(gap_seconds, headroom)
    best = None

    for _ in range(max_rounds):
        if target < 2:
            break
        text = (describe(target) or "").strip()
        if not text:
            break
        actual = synth.duration(text)
        if actual <= budget:
            return Fit(text, round(actual, 3), round(budget, 3), True,
                       trimmed=False)
        best = text
        # Scale the ask by how far over we went, rather than nudging by one word.
        target = max(2, int(target * (budget / actual) * 0.92))

    # The writer could not hit the budget. Fall back to measured truncation,
    # which is allowed to return nothing.
    return fit_measured(best or "", gap_seconds, synth, headroom=headroom) \
        if best else Fit("", 0.0, round(budget, 3), False, True)


@dataclass
class Fit:
    text: str
    seconds: float
    budget: float
    fits: bool
    trimmed: bool = False


def fit(text: str, gap_seconds: float, headroom: float = HEADROOM) -> Fit:
    """Make the text fit, or report honestly that it cannot.

    This is the estimate-only path, for when there is no synthesiser to measure
    against, and two things follow from that.

    The budget holds ESTIMATE_ERROR_S back. The estimator is optimistic by up to
    that much against the reference voice, so without it this function reports
    fits=True for a cue that runs past the end of its gap and onto the next
    line, and reports it confidently, because nothing measured anything. The
    measured paths do not pay this because they have nothing left to be
    uncertain about.

    Trimming goes through the same structural rule as the measured path: drop a
    trailing clause, never cut inside one. Cutting to budget alone produced "A
    man in a grey coat crosses the.", which is inside budget and says nothing,
    and the two paths disagreeing about that is how a rule quietly rots.
    """
    budget = max(0.0, budget_for(gap_seconds, headroom) - ESTIMATE_ERROR_S)
    dur = speech_seconds(text)
    if dur <= budget:
        return Fit(text.strip(), round(dur, 3), round(budget, 3), True)

    # One truncation rule, shared with the measured path. Cutting inside a
    # phrase is what produced "A man in a grey.", and a longer stop list cannot
    # catch that because the offending word is an ordinary adjective. So the cut
    # is structural: drop a trailing clause, or say nothing at all.
    candidate = text.strip()
    while True:
        candidate = _shorten(candidate, 1)
        if not candidate:
            break
        seconds = speech_seconds(candidate)
        if seconds <= budget:
            return Fit(candidate, round(seconds, 3), round(budget, 3), True,
                       trimmed=True)

    # Nothing usable fits. Say so; do not emit a fragment.
    return Fit("", 0.0, round(budget, 3), False, trimmed=True)
