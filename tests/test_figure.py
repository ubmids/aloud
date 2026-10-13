"""The schedule picture: what it draws has to be what the track says."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from aloud.figure import draw, spans


def test_spans_are_the_runs_of_speech():
    mask = np.array([0, 1, 1, 0, 0, 1, 1, 1], dtype=bool)
    assert spans(mask, 0.5) == [(0.5, 1.5), (2.5, 4.0)], spans(mask, 0.5)
    assert spans(np.zeros(4, dtype=bool), 0.5) == []
    print("PASS dialogue runs are found, including one that runs to the end")


def test_every_cue_is_drawn_once_and_named():
    cues = [{"start": 11.5, "end": 14.0, "text": "Rocket engines ignite."},
            # Straddles the four-minute row break, so it is drawn in two parts.
            {"start": 238.0, "end": 242.0, "text": "A man & a robot."}]
    svg = draw(cues, [(1.0, 3.0)], 300.0, "Test")
    assert "Rocket engines ignite." in svg
    assert "A man &amp; a robot." in svg, "text is not escaped for SVG"
    assert svg.count("<rect") == 1 + 2 + 1 + 3, svg.count("<rect")
    assert "2 descriptions" in svg
    print("PASS every cue is drawn, escaped, and split across a row break")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
    print(f"\nall green ({len(fns)} tests)")
