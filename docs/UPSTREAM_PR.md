# Upstream pull request: audio description for the multi-TV app sample

Prepared, not opened. Target: `AmazonAppDev/react-native-multi-tv-app-sample`,
from a fork under `ubmids`, applying
`examples/react-native-multi-tv-app-sample.patch` from
github.com/ubmids/vega-described-track (written against commit `d435082`;
`git apply --check` passes there). Open it only after the patched sample has
been built and run on the Vega Virtual Device, and fill in the "Tested" line
with what was actually seen.

---

**Title:** Add audio description playback to the Vega player screen

**Body:**

Audio description is the second voice that tells a blind or partially
sighted viewer what is on screen, in the silences between the dialogue. This
PR lets the sample's Vega player play a description track when a title has
one, and changes nothing for titles that do not.

What it does:

- Looks for `<stream>.ad.vtt` beside each title's stream. If it is there, it
  is parsed with `vega-described-track`; if not, playback is exactly as
  before.
- Drives the description scheduler from the `currentTime`, `paused` and
  `isVideoBuffering` state that `PlayerScreen.vega.tsx` already keeps. A
  description starts only if the rest of its silence can still hold the
  whole sentence, so a late `timeupdate` never pushes speech onto the next
  line of dialogue. Seeking back re-arms cues; seeking forward drops the ones
  skipped.
- Speaks through one `AudioPlayer` classified as `CONTENT_TYPE_SPEECH` /
  `USAGE_ACCESSIBILITY`, initialised before first use.
- Shows the sentence being said over the video, for sighted co-viewers.

Files: `packages/shared-ui/src/screens/PlayerScreen.vega.tsx` (about 40
lines) and one dependency line in `apps/vega/package.json`.

The track format stays valid WebVTT for every other player; the gap and the
clip ride on the cue identifier:

```
1 audio=cue-001.m4a gap=100.0-106.4
00:01:41.530 --> 00:01:45.980
A grey-haired man lies on a bench while a soldier aims a rifle.
```

Tested: (fill in after the Virtual Device run: which title, which build,
what was heard.)

The library is MIT licensed and was extracted from aloud
(github.com/ubmids/aloud), a Fire TV app that plays open films with
machine-written description.
