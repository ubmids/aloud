# How the no-overlap claim is measured

aloud's one unforgivable failure is speaking over a line of dialogue. The
pipeline checks every track against the gaps it found before writing it
(`Track.validate`), but that check can only be as good as the gap detector: if
the detector misses a line, the check agrees with it. So the claim is measured
separately, against a dialogue map the detector never saw.

## The referee: the film's own production stems

*Tears of Steel* publishes its sound department's stems on
download.blender.org: the full stereo mix (`TOS_DVDSTEREOMIX.aif`) and the same
mix with the dialogue left out (`TOS_MUSIC+FX_NO_DIALOGUE.aif`). Wherever the
two differ inside the speech band, someone is talking.

They are separate masters rather than sample-identical mixes, so they cannot
simply be subtracted (tried first; the residual was as loud as the film). The
comparison is made on speech-band energy (250 to 3500 Hz) in 10 ms frames: the
full mix sits a roughly constant few dB above the music-and-effects mix
everywhere, and rises well clear of that wherever dialogue is added. Frames
3.5 dB above the film's own median difference are dialogue; syllables of one
line are joined across 0.3 s. That gives **{{REF_S}} seconds of dialogue** in
the 12 minute film, including shouted and background lines the English
subtitle file does not carry.

```bash
python3 -m aloud.evaluate tears_of_steel_720p.mov \
  --stems TOS_DVDSTEREOMIX.aif "TOS_MUSIC+FX_NO_DIALOGUE.aif" \
  --captions TOS-en.srt --track out/description.json
```

## The detectors

| listening with | gaps | seconds of gap | gaps touching dialogue | dialogue inside gaps |
|---|---|---|---|---|
{{DETECTOR_ROWS}}

The hand-built detector (speech-band energy plus a 2 to 8 Hz syllable rhythm)
was built and tuned on recorded voices over rain, an orchestral bed and room
tone, and on those it never placed a gap on a line. On a real film it did, 30
times: almost all of them lines spoken over a loud score or an action cue,
where the score's own rhythm hides the syllables. Silero VAD, a small neural
voice detector, fails in different places (it misses quiet and processed
voices the hand-built detector catches), so a frame is speech if either hears
it. The title's caption file is then applied as speech outright, widened 0.4 s
at the front (captions often appear a beat late) and 0.25 s at the back.

Each step only ever removes gap time, so each costs some: 476 seconds of usable
silence become 374. That is the right way round. The cost is fewer or shorter
descriptions; the alternative is a voice over a line.

The 0.9 seconds that remain are four short touches, all at the edge of a long
gap; the longest is 0.34 s inside a forty-second battle. They are as likely to
be the reference catching an effect processed differently between the two
masters as missed speech, and the track-level number below is the one that
matters.

## The shipped track

{{TRACK_RESULT}}

## Reproducing

The stems are 211 MB each and are not in the repository. `aloud/films.py` lists
their URLs beside the film's. The evaluation needs only numpy and ffmpeg.
