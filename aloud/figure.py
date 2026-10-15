"""The whole film's schedule, as a picture.

    python3 -m aloud.figure out/description.json --stems full_mix.aif music_fx.aif \
        --title "Tears of Steel" --out docs/schedule.svg

Audio description cannot be seen, so the claim that it never lands on a line
is hard to show. This draws it: the film in rows of a few minutes, the
dialogue above each row as the film's own production stems hear it (not as
aloud's detector heard it, which would be marking its own homework), and each
description below it. A judge can check the claim by eye: no orange block sits
under a blue one.

Plain SVG with no dependencies, so it renders on GitHub as it is. Every block
carries a `<title>`, which a browser shows on hover.
"""
import argparse
import html
import json
import sys

import numpy as np

# The Signal tokens from design/DESIGN.md, so the figure and the app agree:
# dialogue is the app's mid-tone (3.3:1 on the ground), aloud is caption
# yellow (13.6:1), and the two sit in separate lanes, so neither depends on hue.
GROUND = "#0B0B0A"
INK = "#F4F3EE"
INK_MUTED = "#A3A29B"
RULE = "#3A3A37"
DIALOGUE = "#63635F"
VOICE = "#FFD23F"

ROW_S = 250.0          # at most this much film a row
WIDTH = 1200
LEFT, RIGHT = 120, 24
LANE = 14
ROW_H = 74


def spans(mask: np.ndarray, hop: float) -> list[tuple[float, float]]:
    """Runs of True in a frame mask, as (start, end) seconds."""
    out, start = [], None
    for i, on in enumerate(mask):
        if on and start is None:
            start = i
        elif not on and start is not None:
            out.append((start * hop, i * hop))
            start = None
    if start is not None:
        out.append((start * hop, len(mask) * hop))
    return out


def _clock(t: float) -> str:
    return f"{int(t // 60)}:{int(t % 60):02d}"


def draw(cues: list[dict], dialogue: list[tuple[float, float]], duration: float,
         title: str, note: str = "") -> str:
    # Equal rows, so twelve minutes and fourteen seconds is three rows of a
    # little over four minutes rather than three full rows and a stub.
    rows = max(1, int(np.ceil(duration / ROW_S)))
    row_s = duration / rows
    top = 96
    height = top + rows * ROW_H + 40
    plot_w = WIDTH - LEFT - RIGHT
    x = lambda t, r: LEFT + (t - r * row_s) / row_s * plot_w  # noqa: E731

    spoken = sum(c["end"] - c["start"] for c in cues)
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" font-family="Atkinson Hyperlegible Next, Helvetica, Arial, sans-serif" '
        f'role="img" aria-labelledby="t d">',
        f'<title id="t">{html.escape(title)}: dialogue and descriptions</title>',
        f'<desc id="d">{len(cues)} descriptions, {spoken:.0f} seconds of narration, '
        f'each placed between lines of dialogue.</desc>',
        f'<rect width="{WIDTH}" height="{height}" fill="{GROUND}"/>',
        f'<text x="{LEFT}" y="36" fill="{INK}" font-size="22" font-weight="700">'
        f'{html.escape(title)}: where aloud speaks</text>',
        f'<text x="{LEFT}" y="62" fill="{INK_MUTED}" font-size="14">'
        f'{len(cues)} descriptions, {spoken / 60:.1f} minutes of narration. '
        f'{html.escape(note)}</text>',
    ]
    # Legend, top right: identity is never colour alone, the lanes are named
    # on every row as well.
    lx = WIDTH - RIGHT - 330
    out += [
        f'<rect x="{lx}" y="27" width="14" height="14" rx="3" fill="{DIALOGUE}"/>',
        f'<text x="{lx + 20}" y="39" fill="{INK}" font-size="14">Dialogue (production stems)</text>',
        f'<rect x="{lx}" y="51" width="14" height="14" rx="3" fill="{VOICE}"/>',
        f'<text x="{lx + 20}" y="63" fill="{INK}" font-size="14">aloud describing</text>',
    ]
    for r in range(rows):
        y0 = top + r * ROW_H
        end = min(duration, (r + 1) * row_s)
        out.append(f'<text x="{LEFT - 12}" y="{y0 + 11}" fill="{INK_MUTED}" '
                   f'font-size="12" text-anchor="end">dialogue</text>')
        out.append(f'<text x="{LEFT - 12}" y="{y0 + LANE + 15}" fill="{INK_MUTED}" '
                   f'font-size="12" text-anchor="end">aloud</text>')
        out.append(f'<line x1="{LEFT}" x2="{x(end, r):.1f}" y1="{y0 + LANE + 2}" '
                   f'y2="{y0 + LANE + 2}" stroke="{RULE}" stroke-width="1"/>')
        for a, b in dialogue:
            a, b = max(a, r * row_s), min(b, end)
            if b <= a:
                continue
            out.append(f'<rect x="{x(a, r):.1f}" y="{y0}" width="{max(1.0, x(b, r) - x(a, r)):.1f}" '
                       f'height="{LANE}" rx="2" fill="{DIALOGUE}"><title>dialogue '
                       f'{_clock(a)} to {_clock(b)}</title></rect>')
        for c in cues:
            a, b = max(c["start"], r * row_s), min(c["end"], end)
            if b <= a:
                continue
            out.append(f'<rect x="{x(a, r):.1f}" y="{y0 + LANE + 4}" '
                       f'width="{max(1.5, x(b, r) - x(a, r)):.1f}" height="{LANE}" rx="2" '
                       f'fill="{VOICE}"><title>{_clock(c["start"])} '
                       f'{html.escape(c["text"])}</title></rect>')
        t = np.ceil(r * row_s / 30.0) * 30.0
        while t <= end + 1e-6:
            out.append(f'<text x="{x(t, r):.1f}" y="{y0 + 2 * LANE + 22}" fill="{INK_MUTED}" '
                       f'font-size="11" text-anchor="middle">{_clock(t)}</text>')
            t += 30.0
    out.append("</svg>")
    return "\n".join(out) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="aloud.figure")
    ap.add_argument("track")
    ap.add_argument("--stems", nargs=2, required=True,
                    metavar=("FULL_MIX", "MUSIC_FX"))
    ap.add_argument("--title", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)

    from .evaluate import HOP_S, dialogue_from_stems
    with open(a.track) as f:
        track = json.load(f)
    mask = dialogue_from_stems(*a.stems)
    duration = len(mask) * HOP_S
    svg = draw(track.get("cues", []), spans(mask, HOP_S), duration,
               a.title or track.get("title", "The film"), a.note)
    with open(a.out, "w") as f:
        f.write(svg)
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
