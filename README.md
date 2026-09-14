# Aloud

**A television that describes itself.**

Audio description, the narration track that lets blind and low vision people follow what is
happening on screen, exists for a tiny fraction of content, because producing it is manual
and expensive. Meanwhile every streaming app assumes a viewer who can see it.

Aloud is a Fire TV app for Vega OS that generates audio description live and speaks it into
the gaps between dialogue. A vision model reads frames on a lookahead buffer, a compression
step writes a description sized to fit the silence actually available, and speech lands in
the window before the next line of dialogue.

Close your eyes. The television tells you what you are missing, without ever talking over
anyone.

## The hard part
Gap detection and budget-constrained description. You have to find the silence windows,
predict how long they are, and generate a description that fits without clipping or
overrunning into dialogue. That scheduling problem is the difference between this and a
captioning toy.

## Demo footage
Blender open movies (Sintel, Tears of Steel) so everything shown is freely licensed.

## Status
Scaffold. Architecture gated on one spike: whether Vega OS exposes decoded video frames to
a React Native app. If not, description is generated server-side from the same source the
player streams. See `docs/SPEC.md`.

## Built for
Build, Ship, Shape: Amazon Developer Hackathon 2026, Fire TV track. Deadline 23 Oct 2026.

## Licence
MIT
