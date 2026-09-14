"""Calibrate the duration model against a real synthesiser.

Run: python3 -m aloud.calibrate

Uses macOS `say` because it needs no key and no network. The coefficients it
prints go into budget.py. Rerun it against whichever voice actually ships, since
a different voice has a different rate and the whole scheduling story depends on
this number being real rather than assumed.
"""
import os
import re
import shutil
import subprocess
import tempfile
import wave

from .budget import FIXED_COST_S, SECONDS_PER_SYLLABLE, speech_seconds, syllables

PHRASES = [
    "He turns.",
    "She opens the door.",
    "A man in a grey coat crosses the empty street.",
    "The camera pulls back to reveal a city under heavy snow.",
    "Two children run along the riverbank, laughing.",
    "The dragon lowers its head and looks directly at her.",
    "A single candle burns on the table.",
    "Rain streaks the window as the train pulls out of the station.",
    "He hesitates, then signs the paper.",
    "The room is empty.",
    "Sunlight moves slowly across a wooden floor.",
    "She reads the letter twice, then folds it away.",
    # Digits and heavy punctuation, because the model has terms for both and an
    # unexercised term is an unverified one.
    "The clock reads 3:15.",
    "He counts 24 crates, then stops.",
    "She waits. He does not answer.",
    "Snow, thick and steady, fills the courtyard.",
    "A door slams somewhere above them; the dog barks twice.",
    "The train to platform 9 is delayed by 40 minutes.",
    "Nothing moves.",
    "The old woman smiles, shakes her head, and walks away into the crowd.",
]


def measure(text: str) -> float | None:
    if not shutil.which("say"):
        return None
    with tempfile.TemporaryDirectory() as d:
        aiff = os.path.join(d, "s.aiff")
        wav = os.path.join(d, "s.wav")
        subprocess.run(["say", "-o", aiff, text], check=True, capture_output=True)
        if not shutil.which("ffmpeg"):
            return None
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", aiff, wav],
                       check=True, capture_output=True)
        with wave.open(wav) as w:
            return w.getnframes() / float(w.getframerate())


def main():
    rows = []
    for p in PHRASES:
        actual = measure(p)
        if actual is None:
            print("no synthesiser available, cannot calibrate")
            return
        syl = sum(syllables(w) for w in re.findall(r"[A-Za-z']+", p))
        rows.append((p, syl, actual, speech_seconds(p)))

    # Multivariate least squares over every feature the model actually uses.
    # Fitting syllables alone and substituting the result double-counts the
    # pause terms, which made the model worse rather than better. That mistake
    # is why this fits all five coefficients at once.
    import numpy as np

    A, y = [], []
    for p, syl, actual, _model in rows:
        A.append([1.0, syl, len(re.findall(r"\d", p)),
                  p.count(",") + p.count(";"), len(re.findall(r"[.!?]", p))])
        y.append(actual)
    coef, *_ = np.linalg.lstsq(np.array(A), np.array(y), rcond=None)
    fixed, per_syl, per_digit, per_comma, per_stop = coef

    print(f"{'phrase':<58} {'syl':>4} {'actual':>7} {'model':>7} {'err':>7} {'fitted':>7}")
    worst = worst_fit = 0.0
    for (p, syl, actual, model), row in zip(rows, A):
        fitted = float(np.dot(row, coef))
        worst = max(worst, abs(model - actual))
        worst_fit = max(worst_fit, abs(fitted - actual))
        print(f"{p[:56]:<58} {syl:>4} {actual:>7.2f} {model:>7.2f} "
              f"{model - actual:>+7.2f} {fitted - actual:>+7.2f}")

    print(f"\ncurrent model   worst error: {worst:.2f}s")
    print(f"refitted model  worst error: {worst_fit:.2f}s")
    print("\ncoefficients for budget.py:")
    print(f"  FIXED_COST_S         = {fixed:.3f}   (currently {FIXED_COST_S})")
    print(f"  SECONDS_PER_SYLLABLE = {per_syl:.3f}   (currently {SECONDS_PER_SYLLABLE})")
    print(f"  SECONDS_PER_DIGIT    = {per_digit:.3f}")
    print(f"  PAUSE_COMMA_S        = {per_comma:.3f}")
    print(f"  PAUSE_STOP_S         = {per_stop:.3f}")
    print(f"\nSAFETY_MARGIN_S should be at least {worst_fit:.2f}s, the worst "
          "residual, so a description that the model says fits actually does.")


if __name__ == "__main__":
    main()
