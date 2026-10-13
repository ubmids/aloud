# Aloud spec

## Spike result: Vega OS does NOT expose decoded video frames

Vega media playback is W3C Media (HTMLMediaElement, MSE, EME) running on GStreamer with
hardware-accelerated decode and render. There is no documented path to decoded frames from
app JavaScript: no canvas drawImage, no requestVideoFrameCallback, no texture access.

What the player *does* expose is enough:

- Properties: `currentTime`, `duration`, `paused`, `volume`
- Events: `timeupdate`, `ended`, `error`, `loadedmetadata`

## Architecture decision

Descriptions are generated **server-side from the source video** into a timed description
track. The Vega app plays the video and fires each description from `timeupdate` against
`currentTime`.

This is the better architecture regardless of the frame question:

- It is how real audio description already works, as a timed track, so the output is a
  standard artefact rather than a bespoke gimmick.
- It is cacheable. Describe a title once, serve it to everyone.
- It splits the two risks apart. The hard problem lives in a backend that can be built and
  tested today with no Vega SDK, and the app becomes a thin, well-synchronised player.

## The hard part, unchanged

Gap detection and budget-constrained description.

1. Find the silence windows in the dialogue track.
2. Predict each window length.
3. Generate a description that fits the window when spoken, without clipping or overrunning
   into the next line.

Budget is measured in speech duration, not characters, so the generator is constrained by
a TTS duration estimate and re-compressed if it overruns.

## Components

- `backend/` describe pipeline: scene segmentation, silence detection, vision captioning,
  duration-budgeted compression, TTS, timed track emission
- `app/` Vega OS React Native player, description scheduler on `timeupdate`, settings surface
  (verbosity, voice, density)

## Demo footage
Blender open movies (Sintel, Tears of Steel). Freely licensed, safe to publish.

## Amazon mini-challenge pairing
AWS Builder. Frame understanding runs through Amazon Bedrock, integration documented.
