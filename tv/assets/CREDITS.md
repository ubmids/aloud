# Bundled media

## sintel-trailer.mp4

The trailer for **Sintel**, an open movie by the Blender Foundation.

- (c) copyright Blender Foundation | <https://durian.blender.org>
- Licence: [Creative Commons Attribution 3.0](https://creativecommons.org/licenses/by/3.0/)
- Source: <https://download.blender.org/durian/trailer/sintel_trailer-720p.mp4>

Re-encoded for this app, which is permitted by the licence:

```
ffmpeg -i sintel_trailer-720p.mp4 -vf scale=640:-2 -c:v libx264 -profile:v main \
  -level 3.1 -crf 26 -preset slow -pix_fmt yuv420p -c:a aac -b:a 96k -ac 2 \
  -movflags +faststart sintel-trailer.mp4
```

1280x720 to 640x360, 7.6MB to 1.9MB. Nothing was cut; the 52 second trailer is
complete. The re-encode exists because this file ships inside the app package
and inside a git repository, and neither is a good home for 7.6MB of video.

## cues/

`cue-01.m4a` through `cue-04.m4a` are the spoken descriptions, synthesised by
the backend in `aloud/synth.py` from macOS `say` and converted to AAC. They are
generated artefacts, committed because the app needs them at runtime and the
device has no synthesiser of its own. Regenerate them by running the backend
over `sintel-trailer.mp4`; the filenames are assigned in cue order.
