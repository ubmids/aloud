"""Measuring a track against where people actually talk.

    python3 -m aloud.evaluate film.mov --stems full_mix.aif music_fx.aif \
        [--captions film.srt] [--track out/description.json]

The safety claim is that no description lands on dialogue, and the pipeline's
own check (`Track.validate`) can only test that against the gaps the pipeline
itself found. If the detector is wrong, the check agrees with it. This module
is the independent referee.

Some films publish their production stems: the full mix, and the same mix with
the dialogue left out. *Tears of Steel* does, on download.blender.org. Where
those disagree inside the speech band, someone is talking. That gives a
dialogue map the detector never saw, built from the film's own sound
department, and every number in the README about overlap comes from it.

The two stems are separate masters rather than sample-identical mixes, so they
cannot simply be subtracted (that was tried, and the residual was as loud as
the film). The comparison is done on speech-band energy instead: the full mix
sits a roughly constant few dB above the music-and-effects mix everywhere,
and rises well clear of that wherever dialogue is added.
"""
import argparse
import json
import sys

import numpy as np

from .gaps import FRAME_MS, find_gaps, load_audio

HOP_S = 0.01
RISE_DB = 3.5      # above the film's own baseline difference
CLOSE_S = 0.3      # join syllables of the same line


def _band_energy(x: np.ndarray, sr: int, hop: int, win: int = 512) -> np.ndarray:
    n = max(0, (len(x) - win) // hop)
    out = np.empty(n, dtype=np.float64)
    hann = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    band = (freqs >= 250) & (freqs <= 3500)
    for i0 in range(0, n, 4096):
        idx = np.arange(win)[None, :] + hop * np.arange(i0, min(n, i0 + 4096))[:, None]
        spec = np.abs(np.fft.rfft(x[idx] * hann, axis=1)) ** 2
        out[i0:i0 + len(idx)] = spec[:, band].sum(axis=1)
    return out


def _close(mask: np.ndarray, frames: int) -> np.ndarray:
    out = mask.copy()
    on = np.flatnonzero(mask)
    for a, b in zip(on[:-1], on[1:]):
        if 1 < b - a <= frames:
            out[a:b] = True
    return out


def dialogue_from_stems(full_mix: str, music_fx: str, *, sr: int = 16000,
                        rise_db: float = RISE_DB) -> np.ndarray:
    """True for every 10ms frame where the stems say someone is speaking."""
    mix, _ = load_audio(full_mix, sr)
    bed, _ = load_audio(music_fx, sr)
    n = min(len(mix), len(bed))
    hop = int(sr * HOP_S)
    ratio = 10 * np.log10((_band_energy(mix[:n], sr, hop) + 1e-6)
                          / (_band_energy(bed[:n], sr, hop) + 1e-6))
    baseline = float(np.median(ratio))
    return _close(ratio > baseline + rise_db, int(CLOSE_S / HOP_S))


def overlap_seconds(mask: np.ndarray, start: float, end: float) -> float:
    a, b = max(0, int(start / HOP_S)), max(0, int(end / HOP_S))
    return float(mask[a:b].sum()) * HOP_S


def gap_report(name: str, gaps, mask: np.ndarray, tolerance: float = 0.1) -> dict:
    bad = [(g, overlap_seconds(mask, g.start, g.end)) for g in gaps]
    bad = [(g, o) for g, o in bad if o > tolerance]
    return {"detector": name, "gaps": len(gaps),
            "gap_seconds": round(sum(g.duration for g in gaps), 1),
            "gaps_touching_dialogue": len(bad),
            "dialogue_seconds_inside_gaps": round(sum(o for _, o in bad), 1)}


def cue_report(track: dict, mask: np.ndarray) -> dict:
    cues = track.get("cues", [])
    hits = []
    for c in cues:
        o = overlap_seconds(mask, c["start"], c["end"])
        if o > 0:
            hits.append({"start": c["start"], "end": c["end"],
                         "overlap": round(o, 2), "text": c["text"]})
    return {"cues": len(cues),
            "spoken_seconds": round(sum(c["end"] - c["start"] for c in cues), 1),
            "cues_touching_dialogue": len(hits),
            "seconds_spoken_over_dialogue": round(sum(h["overlap"] for h in hits), 2),
            "touching": hits}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aloud.evaluate")
    ap.add_argument("video")
    ap.add_argument("--stems", nargs=2, metavar=("FULL_MIX", "MUSIC_FX"),
                    required=True)
    ap.add_argument("--captions")
    ap.add_argument("--track")
    ap.add_argument("--json", help="write the report here as well")
    a = ap.parse_args(argv)

    mask = dialogue_from_stems(*a.stems)
    audio, sr = load_audio(a.video)
    also = None
    if a.captions:
        from .captions import speech_spans
        also = speech_spans(a.captions)

    report = {"dialogue_seconds_in_reference": round(mask.sum() * HOP_S, 1),
              "detectors": [
                  gap_report("hand-built ear only",
                             find_gaps(audio, sr, vad=False), mask),
                  gap_report("hand-built ear + Silero VAD",
                             find_gaps(audio, sr, vad=True), mask)]}
    if also:
        report["detectors"].append(gap_report(
            "both ears + the caption file",
            find_gaps(audio, sr, vad=True, also_speech=also), mask))
    if a.track:
        with open(a.track) as f:
            report["track"] = cue_report(json.load(f), mask)

    for d in report["detectors"]:
        print(f"{d['detector']:32s} {d['gaps']:4d} gaps, {d['gap_seconds']:6.1f}s, "
              f"{d['gaps_touching_dialogue']:3d} touching dialogue, "
              f"{d['dialogue_seconds_inside_gaps']:5.1f}s of it")
    if "track" in report:
        t = report["track"]
        print(f"\ntrack: {t['cues']} cues, {t['spoken_seconds']}s spoken, "
              f"{t['cues_touching_dialogue']} touching dialogue, "
              f"{t['seconds_spoken_over_dialogue']}s over it")
        for h in t["touching"]:
            print(f"  {h['start']:7.2f}-{h['end']:7.2f}  {h['overlap']}s  {h['text']}")
    if a.json:
        with open(a.json, "w") as f:
            json.dump(report, f, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
