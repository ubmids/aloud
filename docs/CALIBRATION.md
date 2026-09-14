# Calibration

Three constants in this pipeline are measured rather than chosen. Each one was
a guess first, and each guess was wrong in a way that only showed up when it was
checked against a real synthesiser.

Regenerate with `python3 -m aloud.calibrate`.

## Duration is measured, not predicted

The first design estimated how long a description would take to say, from
syllable counts. Calibrated against the reference voice over 20 phrases, the
worst residual was **0.62 seconds**. Against a gap of a second and a half that
is the difference between a description and an interruption.

Refitting all five coefficients at once did not save it: the least squares fit
returned a **negative** fixed cost, which is physically impossible and a sign
the linear model was absorbing the pause terms into the intercept. Worst
residual improved only from 0.66s to 0.62s.

So the pipeline synthesises the candidate and measures it. The estimator
survives only as a first guess for how many words to ask for, where being half
a second out costs nothing.

## MIN_GAP_S = 1.35s

Originally 0.9s, chosen because it sounded about right. Measuring the shortest
descriptions worth saying:

| description | spoken | gap needed at 85% headroom |
|---|---|---|
| He waits. | 0.64s | 0.75s |
| A man. | 0.65s | 0.76s |
| She turns. | 0.77s | 0.91s |
| Snow falls. | 0.91s | 1.07s |
| Nothing moves. | 0.99s | 1.16s |
| A man crosses. | 1.10s | 1.29s |
| A door opens. | 1.19s | 1.40s |

A 0.9s gap holds 0.77s of speech and cannot carry most of these. Reporting such
gaps only sends the describer off to write something that can never be
scheduled, so the detector now discards them.

## BAND_RMS_FLOOR = 0.005, absolute

The loudness gate started as a percentile of the track's own energy. That made
the decision for one frame depend on the rest of the file: a fixture containing
a silent passage passed, and the identical code on a track without one reported
an entire film as a single gap, because the percentile had risen into the
dialogue.

It is now an absolute floor on energy inside the speech band. Audio is
normalised to plus or minus one, so the threshold means the same thing
everywhere, and `test_detection_does_not_depend_on_unrelated_content` pins it.

Separation on the synthetic fixtures, where 1.0 is entirely speech-shaped:

| content | speechiness |
|---|---|
| speech | 0.99 |
| music | 0.09 |
| room tone | 0.00 |

## SPEECH_LOW = 200Hz, not 300Hz

The telephone band starts at 300Hz. A detector that starts there discards the
fundamental of most male voices, which sit between 85 and 255Hz, and scores them
as non-speech. 200Hz keeps enough of it without admitting the low rumble that
scores and room tone occupy.
