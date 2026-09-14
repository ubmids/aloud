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

## Speech needs two conditions, not one

The detector originally asked one question: what fraction of a frame's energy
sits in the speech band. Measured against real voices instead of the synthetic
fixture, that question does not work.

| content | speech-band score |
|---|---|
| rain | 0.76 |
| real voices | 0.52 to 0.66 |
| orchestral bed | 0.29 |
| engine rumble | 0.19 |
| room tone | 0.00 |

Rain scores **higher than every human voice**. Broadband sound spreads energy
right across the speech band, so a band-only detector hears dialogue through an
entire rainy scene and never emits a single description. Applause, crowds, wind
and static all behave the same way.

What separates them is rhythm. A person opens and closes their mouth a few times
a second, which puts a strong peak in the amplitude envelope between 2Hz and
8Hz. Rain has no such rhythm.

| content | syllable rhythm |
|---|---|
| real voices | 0.61 to 0.78 |
| orchestral bed | 0.40 |
| applause | 0.27 |
| rain | 0.23 |
| room tone | 0.21 |

Speech now requires **both**: speech-shaped energy says the sound could be a
voice, the syllable rhythm says something is actually talking.

## CLOSE_S = 0.25s then OPEN_S = 0.20s, in that order

A music bed misreads a small fraction of its frames as speech. That scatter does
not shrink a gap, it destroys it: a three and a half second gap broken every
quarter second becomes several runs too short to use and disappears entirely.
Measured, a bed misreading only 7.4% of its frames lost its whole gap.

Two attempts at cleaning it up both leaked into dialogue.

1. A symmetric majority vote over a sliding window removed the scatter and ate
   60ms off the end of a real line, because a symmetric filter shrinks a run
   from both sides.
2. Dropping short speech runs outright leaked 0.5s, because the quiet tail of a
   line fragments into short runs and is genuinely speech.

Closing before opening fixes both: the tail is reattached to its line before
anything becomes eligible to be dropped. Grid search over a track of real
voices, rain, an orchestral bed and room tone:

| close | open | dialogue overlap | quiet recovered |
|---|---|---|---|
| 0.00 | 0.10 | 0.12s | 9.3s |
| 0.00 | 0.20 | 0.50s | 9.6s |
| 0.00 | 0.30 | 4.32s | 14.2s |
| **0.20+** | **any** | **0.00s** | **6.1s** |

Closing costs gap time, because it also joins scattered frames inside a music
bed. 6.1s of 10s recovered instead of 9.3s. That is the right way round: three
seconds less description is a fair price for never speaking over a line, which
is the one thing this system must not do.

## SPEECH_LOW = 200Hz, not 300Hz

The telephone band starts at 300Hz. A detector that starts there discards the
fundamental of most male voices, which sit between 85 and 255Hz, and scores them
as non-speech. 200Hz keeps enough of it without admitting the low rumble that
scores and room tone occupy.
