# Friction log: building a video app for Vega OS

Recorded while building Aloud, a Fire TV app that speaks audio description into
the gaps between dialogue, between 14 September and submission. Every entry is
something that actually cost time on this build, in the format the hackathon
rules ask for: task attempted, steps taken, expected versus actual, severity,
workaround, suggestion.

Entries are ordered by how much they would cost a developer who hits them cold.
Nothing here is hypothetical. Each one is reproducible from this repository, and
where the resolved behaviour is pinned by a test or a file, it is named.

The shape of the day is worth stating up front, because it is the finding rather
than the sum of the findings. A React Native app that compiles, typechecks,
packages, installs, launches and demuxes its video file still cannot show a
frame, and every distinct reason it cannot reports as the same four-word error.

---

## 1. Adding the media package gets you the module and none of the services

**Severity: critical.** Nothing plays until it is fixed, and nothing in the
toolchain points at it.

**Task attempted.** Play a bundled MP4 in a React Native app using
`@amazon-devices/react-native-w3cmedia`.

**Steps taken.** Created the project with `vega project generate`, added the
`@amazon-devices/react-native-w3cmedia` dependency, mounted the `Video`
component, built, installed and launched.

**Expected.** That a dependency whose entire purpose is media playback would
arrive able to play media, or failing that, that the build would say what else
was needed. Autolinking already edits the manifest during the build: the log
prints `Found dependencies to add to the manifest` and inserts
`/com.amazon.kepler.w3cmedia_2@IW3cmedia_3` without being asked.

**Actual.** The manifest gets the module and none of the platform services the
media pipeline actually talks to. The app builds clean, `manifest validation
found 0 errors`, installs, launches, opens the file and demuxes it. Then the
video sink has no window handle, the decoder cannot attach as a writer to a
buffer queue that was never created, and playback fails.

The application-visible error is `MEDIA_ERR_SRC_NOT_SUPPORTED`, which says codec.
The cause is only in the device log, and it is unambiguous once you find it:

```
Binder: Unable connect to 'com.amazon.mediabuffer.service'.
Binder: Unable connect to 'com.amazon.audio.control'.
Binder: Unable connect to 'com.amazon.audio.stream'.
Binder: Unable connect to 'com.amazon.mediametrics.service'.
ERROR ... Cannot connect! Failed to bind to service! IPCN returned IPCN_ERR_REMOTE_ERROR
[com.amazon.kepler.buffer_queue.BufferQueueError]: Proxy could not connect to
  server: Failed to attach as writer
```

Nine `[[wants.service]]` entries and one `[[needs.privilege]]` are required.
Searching the W3C media documentation, the component reference and the packaged
`README.md` for any of the service ids turned up nothing. Where they were
eventually found was the manifest of the sample app at
`github.com/AmazonAppDev/vega-video-sample`, spread across the file under
comments like `# Required for GIPC SR? it's for audio video playback`, a
question mark included. A developer who has not thought to read another
repository's manifest has no obvious path to this.

**Workaround.** Read the device log, map each `Unable connect to` line back to a
service id, and declare them. `tv/manifest.toml` now carries
`com.amazon.media.server`, `com.amazon.mediametrics.service`,
`com.amazon.media.playersession.service`, `com.amazon.mediabuffer.service`,
`com.amazon.mediatransform.service`, `com.amazon.gipc.uuid.*`,
`com.amazon.audio.stream`, `com.amazon.audio.control`, `com.amazon.audio.system`
and the privilege `com.amazon.media.secureplayback`. With those in place the
film plays first try.

**Suggestion.** Three things, in order of value. Put the complete manifest block
for basic playback in the W3C media documentation as a copyable snippet, before
the API reference, because it is a precondition for every line that follows it.
Have autolinking add these the way it already adds the module, since the
packaging tool clearly knows how to write to the manifest. And at minimum, make
the packaging tool warn: it already emits a warning of exactly this shape
elsewhere, "MAY require the privilege ... but the privilege is not requested in
the manifest", so the mechanism exists and is simply not wired to the media
services.

---

## 2. Every distinct media failure reports as the same error, with no detail

**Severity: critical**, and it is what turned each entry below into its own
investigation rather than a five minute fix.

**Task attempted.** Work out why a video would not play.

**Steps taken.** Handled `onError` on the `Video` component and read the
`MediaError` code.

**Expected.** Enough to distinguish a missing file from a missing permission
from an unsupported codec, since those are different problems with different
fixes and the platform knows which one occurred.

**Actual.** Four separate causes, each with a different fix, all reporting
`MEDIA_ERR_SRC_NOT_SUPPORTED` (code 4) and an empty message:

- the file was at a path the player cannot read (`require`-resolved asset URL)
- the path was correct but carried a `file://` scheme the player does not parse
- the manifest was missing the media service declarations
- the source was attached before the video surface existed

The native layer logs `makeMediaError: code= 4 msg =` with the message field
blank, so the detail is discarded at the boundary rather than absent upstream.
One layer down, GStreamer had already printed the precise cause in every case.

**Workaround.** Stopped trusting the error entirely and worked from
`vega device start-log-stream`, grepping for `GSTLOG`, `Binder`, `W3CMEDIA` and
`makeMediaError` together. Every one of the four causes was obvious in the log
within seconds of looking at the right lines.

**Suggestion.** Populate the `msg` field. The information exists at the point
the error is constructed; passing through even the GStreamer error string would
have removed most of a day from this build. Failing that, document the mapping
between the codes an app receives and the log lines that explain them, so the
first thing a developer reads is "code 4 usually means one of these four things,
here is what to grep for".

---

## 3. The `Video` component ignores `style` and sizes itself to NaN by default

**Severity: high.** Silent, and the symptom appears three layers away from the
cause.

**Task attempted.** Fit the video to a region of the screen alongside other UI.

**Steps taken.** Did what every other React Native component wants, and passed
`style={StyleSheet.absoluteFill}` on a positioned parent.

**Expected.** A React Native component to lay out like a React Native component.
`Video` accepts `ViewProps`, which includes `style`, so it typechecks.

**Actual.** `style` is discarded, and nothing in the documentation or the
component's own TypeScript signature says so. Reading
`node_modules/@amazon-devices/react-native-w3cmedia/dist/interface/Video.js`
shows `render()` returning `<View style={{ width: this.width, height:
this.height }}>` and nothing else, where `width_` and `height_` are initialised
to `NaN` and only set from the `width` and `height` props. With no such props the
component lays out at NaN by NaN, the native surface underneath is never
created, and the only trace is a GStreamer warning:

```
keplervideosink, gstkeplervideosink.cpp, 908, gst_keplervideosink_set_window_handle,
  <video-sink>, overlay handle is NULL!
```

which then cascades into the decoder failing to attach to a buffer queue. It
looks like a decoder problem. It is a layout problem.

**Workaround.** Measured the containing view with `onLayout` and passed the
resulting pixel dimensions as numeric `width` and `height` props. See
`measureStage` in `tv/src/App.tsx`. The layout stays declarative and the player
gets the two numbers it insists on.

**Suggestion.** Either honour `style`, which is what the type signature promises
by accepting `ViewProps`, or drop `ViewProps` from the signature and make
`width` and `height` required so the compiler catches it. If neither, say in the
documentation, in the first example, that these props are mandatory and that
omitting them produces no picture and no error.

---

## 4. Setting `src` as a prop attaches the source before the surface exists

**Severity: high.** The correct-looking code is the broken code.

**Task attempted.** Point the player at a file and play it.

**Steps taken.** Passed `src` and `autoplay` as props on `<Video>`, which is how
the component's own prop list presents them.

**Expected.** Declarative props on a declarative component.

**Actual.** The player applies `props.src` during its initialisation, which
completes before the native video surface has been created and registered. The
pipeline is therefore constructed with no video sink attached. The surface
arrives a moment later and the log states the outcome in three words:

```
MediaElement::on_surface_registered: pipeline already created
```

Ordering is visible in the log and is always the same: `MediaPlayer: load` first,
`KeplerVideoSurfaceView: onKeplerVideoSurfaceViewCreated` second.

**Workaround.** Mount `<Video>` with no `src`, then attach the film one beat
after `onComponentDidMount` reports the player ready, by which time the surface
has been registered, and call `play()` from `onLoadedMetadata` rather than
relying on `autoplay`. See `handlePlayerReady` in `tv/src/App.tsx`.

The delay is the unsatisfying part and it is unavoidable: there is no public
callback for surface attachment. `onSurfaceCreated` exists on the component but
is marked `@hidden` and is not exposed as a prop, so an app cannot wait on the
one event it needs to wait on.

**Suggestion.** Expose surface attachment as a prop callback, or have the
component defer applying `src` until the surface is registered, which it is
already tracking internally in `maybeSetSurface`. Either removes the timer. This
is a small change inside the component and it would make the obvious code work.

---

## 5. Bundled media cannot be referenced through `require`, and `file://` breaks it

**Severity: high.**

**Task attempted.** Play a video file shipped inside the app package.

**Steps taken.** Put the file in the project, `require`d it, and resolved it with
`Image.resolveAssetSource`, which is the standard React Native way to turn a
packager handle into a URL and works for every other asset type.

**Expected.** A URL the player can open. Metro treats `mp4` and `m4a` as assets
by default, the packager copies them, and they appear in the `.vpkg`.

**Actual.** Three failures in a row, each reporting as `MEDIA_ERR_SRC_NOT_SUPPORTED`:

1. `resolveAssetSource` returns `file:///pkg/bundle/assets/assets/<name>.mp4`,
   resolved relative to the JavaScript bundle. The native pipeline reads the
   package mount, not the bundle directory, and cannot open it.
2. The packaged copy that *is* readable is the verbatim copy of the project's
   `assets/` directory, which the OS mounts at `/pkg/assets`. This is not stated
   anywhere the developer is looking.
3. Even with the right directory, and with no statement anywhere that a scheme
   is unwelcome, `file:///pkg/assets/<name>.mp4` fails, because
   the string is handed to GStreamer's `filesrc` as a *filename* rather than
   parsed as a URI. The log makes this unmistakable once seen, since the scheme
   is inside the quoted filename:

   ```
   filesrc, gstfilesrc.c, 553, gst_file_src_start, <filesource>,
     error: No such file "file:///pkg/assets/sintel-trailer.mp4"
   ```

So the working answer is a plain absolute path with no scheme, `/pkg/assets/<name>.mp4`,
which is the one form a developer coming from the web platform is least likely
to try, on a component whose entire selling point is W3C semantics.

**Workaround.** Reference package paths directly and drop `require` for media
entirely, which also removes the duplicate copy the packager was shipping. See
`tv/src/player/assets.ts`.

**Suggestion.** Document the package asset path in the media player guide with a
worked example, and accept `file://` URIs on `src` by parsing them, since the
component's premise is that web semantics carry over. If `file://` is genuinely
unsupported, reject it with a distinct error rather than looking up a filename
with a scheme in it.

---

## 6. The platform never states that decoded frames are unavailable to app JavaScript

**Severity: high**, and uniquely so, because it is the one entry here that
changes what you build rather than how long it takes.

**Task attempted.** Decide the architecture of an app that must look at the
picture. Aloud describes what is on screen, so the first question is whether the
app can see it.

**Steps taken.** Read the W3C media documentation and the component reference
looking for canvas access, a frame callback, `requestVideoFrameCallback`, a
texture handle, anything.

**Expected.** A clear statement either way, since it is the difference between an
app that analyses video on device and an app that cannot.

**Actual.** No statement either way. The answer has to be inferred from an
architecture note about hardware-accelerated GStreamer decode, which describes
the pipeline without ever drawing the conclusion that follows from it: frames go
from the decoder to a hardware surface and never pass through JavaScript.
Confirmed the inference the only way available, by reading every type definition
the package ships and finding no frame access, no canvas, no
`requestVideoFrameCallback` and no texture handle anywhere in them.

This single undocumented fact determines the entire architecture of any app
doing visual analysis. Get it wrong and you build the wrong thing for a week.

**Workaround.** Built the analysis into a backend that reads the source file and
emits a timed description track, with the app scheduling the track against
`currentTime`. This turned out to be the better architecture anyway, for reasons
that have nothing to do with the constraint: it is how professional audio
description already ships, it is cacheable, and a human describer can review a
track before it goes out. But that is luck, not guidance.

**Suggestion.** One sentence, early, in the media player overview: "Decoded video
frames are not available to application JavaScript. Video is decoded in hardware
and rendered directly to a surface." Then say what an app should do instead. The
cost of the sentence is nothing and the cost of its absence is a rewrite.

---

## 7. `AudioPlayer` fails silently if you skip `initialize()`

**Severity: medium to high.** No error, anywhere, at any layer.

**Task attempted.** Play a short pre-synthesised speech clip over the film,
using a second player so the film's own audio keeps running underneath.

**Steps taken.** Constructed `new AudioPlayer(contentType, usageType)`, set
`src`, called `play()`.

**Expected.** Sound, or an error.

**Actual.** Neither. `src` is accepted, `play()` returns, and nothing happens.
The device log shows no pipeline being created for the player and no error of
any kind. The player requires `await initialize()` first, which is stated in the
class doc comment in the `.d.ts` and in the package README, and nowhere that a
developer following the component-first path would pass.

The failure mode is the worst kind for an accessibility feature specifically:
the descriptions were being scheduled correctly, the cue text was appearing on
screen, and the thing simply made no sound. Everything looked right.

**Workaround.** Initialise in the constructor, track readiness, and refuse to
speak until ready. A cue arriving before the player is initialised is dropped
rather than queued, which is the correct behaviour here: a description that
arrives late lands on the dialogue it was supposed to avoid. See
`tv/src/player/speech.ts`.

**Suggestion.** Throw from `src` or `play()` when the player is not initialised.
A loud failure on a required setup step costs a developer one run; a silent one
cost this build an evening of assuming the scheduler was at fault.

---

## 8. `vega project generate` overwrote `.gitignore` on a repo destined to go public

**Severity: high.** It is a small bug with a security shape.

**Task attempted.** Add a Vega app to an existing repository.

**Steps taken.** Ran `vega project generate` with the repository as the output
directory.

**Expected.** Generated files added, existing files left alone, or at worst a
prompt before touching anything that already existed.

**Actual.** The existing `.gitignore` was replaced rather than merged, wiping
the rules that block secrets from a repository that goes public before
submission. The generator also wrote into the output directory's root rather
than a subdirectory, scattering `app.json`, `index.js`, `src/`, `test/` and
`package.json` into an existing project alongside unrelated files.

Losing a `.gitignore` is quiet. Nothing fails, nothing warns, and the next
`git add` is the one that notices, if anyone is looking.

**Workaround.** Restored the rules by hand and moved the generated project into
`tv/`.

**Suggestion.** Never overwrite `.gitignore`. Append the generated rules to an
existing file, or write `.gitignore.vega` and say so. Refuse to generate into a
non-empty directory without an explicit flag. Both are one-line changes and the
current behaviour can silently publish a developer's keys.

---

## 9. `npm install` of the Kepler package times out with no warning

**Severity: medium**, and it disproportionately affects developers on slower
connections, which for this build meant Lagos.

**Task attempted.** Install dependencies.

**Steps taken.** `npm install`.

**Expected.** It to finish, or to say why not.

**Actual.** It failed after 314 seconds fetching
`@amazon-devices/react-native-kepler`, which is large enough that npm's default
timeout is simply too short for it on an ordinary connection. Nothing in the
setup instructions mentions this, so the natural reading of the failure is that
the registry is down or the package name is wrong.

**Workaround.** `npm install --fetch-timeout=1800000 --fetch-retries=5`, which is
now in this repository's README so the next person does not have to work it out.

**Suggestion.** Put that flag in the getting-started instructions with a sentence
explaining why. It costs one line and removes a first-hour failure that looks
like a broken SDK rather than a slow download.

---

## 10. Enum member names are not in the prose documentation

**Severity: low to medium.** Quick to fix once you know to open the type
definitions, which is the whole problem.

**Task attempted.** Classify the description audio as accessibility speech, so
the platform can treat it correctly against the film rather than leaving the
decision to luck. This matters for an accessibility app: the description is a
second stream that must coexist with the first, not replace it.

**Steps taken.** Looked for the members of `AudioContentType` and
`AudioUsageType` in the documentation.

**Expected.** A list of the values, given that choosing between them is the
entire point of the two parameters.

**Actual.** The types are named in the prose, the members are not. The obvious
guesses, `AudioContentType.SPEECH` and `AudioUsageType.ACCESSIBILITY`, are both
wrong. The real names are `CONTENT_TYPE_SPEECH` and `USAGE_ACCESSIBILITY`, found
by reading `dist/interface/MediaTypes.d.ts`. `USAGE_ACCESSIBILITY` in particular
is worth surfacing, since an app that does not know it exists will classify
accessibility audio as generic media and lose the platform's help.

**Workaround.** Read the `.d.ts`. See `tv/src/player/speech.ts`.

**Suggestion.** Include the enum members in the API reference. If the reference
is generated from the TypeScript, these are already annotated and simply are not
being emitted.

---

## 11. The device shell cannot see the app's own package, so you cannot verify what shipped

**Severity: medium.** A diagnosis cost rather than a build cost, but it applies
to every entry above that involves a file path.

**Task attempted.** Check whether the video file was where the player was
looking for it.

**Steps taken.** `vega device run-cmd -c "ls -la /pkgs"` and variations.

**Expected.** To see the installed application package and confirm or refute the
path in one command.

**Actual.** The shell runs in its own mount namespace and sees only its own
package. `/pkg` is a symlink to `/pkgs/com.amazon.dev.shell`, and the installed
app does not appear anywhere the shell can reach. So the one question worth
asking, is the file where I think it is, cannot be answered directly, and the
path has to be inferred from log lines and from the `.vpkg` contents on the
host.

**Workaround.** Listed the package with `unzip -l` on the host to see the layout,
then determined the mount point from log output. Correct, but indirect.

**Suggestion.** A `vega device ls-package <id>` or a documented note on where an
installed package's assets live on device, with the caveat that the shell cannot
reach them, would close this. Stating the `/pkg/assets` convention in the docs
would remove the need for it entirely.

---

## 12. The `build_number is 0` warning does not say what it should be

**Severity: low.**

**Task attempted.** Produce a submission-ready package.

**Steps taken.** Ran the build and read the warnings.

**Expected.** Either a sensible default or guidance.

**Actual.** `WARNING: build_number is 0. Provide via --build-number CLI option or
in manifest.toml [package] section.` It says where to put it and not what it is
for, so a first-time submitter cannot tell whether it must be unique per upload,
monotonic, matched to the version string, or whether zero is merely untidy. The
warning fires on every build of every new project, so its most likely fate is to
be ignored, which is the wrong outcome if it turns out to matter at submission.

**Workaround.** Set `build-number = 1` in `[package]` and moved on.

**Suggestion.** One clause: "This must increase with each build you upload to the
Appstore." Then a developer knows whether to care.

---

## What went well, since a friction log that only complains is not useful

- The device log is genuinely excellent. Every single failure in this document
  was already explained correctly somewhere in `vega device start-log-stream`,
  usually in one line naming the exact element and the exact reason. The problem
  throughout was never that the platform did not know what was wrong, only that
  it did not tell the app. That is a much better position to be in than the
  reverse, and most of these entries are fixable by forwarding information the
  system already has.

- Shipping the TypeScript definitions with real doc comments meant every
  undocumented thing here was still *discoverable*. `initialize()` being
  required, the enum member names, `Video.render()` ignoring `style`: all of it
  was answerable by reading `node_modules`. An SDK that ships readable sources is
  one a determined developer cannot be permanently blocked by.

- `vega virtual-device` is fast and reliable. It boots in well under a minute,
  `vega run-app` installs and launches in one command, and across roughly fifteen
  build-install-run cycles it never once needed restarting or wedged. The
  iteration loop was never the bottleneck, which is the thing that usually goes
  wrong with device emulators.

- The manifest validator is strict in the right way. Adding ten service
  declarations by hand to a TOML file is exactly the kind of edit that produces a
  typo, and `manifest validation found 0 errors` meant the one thing that could
  have compounded the confusion in entry 1 never did.

- The sample app at `github.com/AmazonAppDev/vega-video-sample` is real, complete
  and current. It is the reason entry 1 took an afternoon instead of the whole
  build. It deserves to be linked from the media player documentation as
  required reading rather than as further reading, because right now it is
  carrying load the documentation should be carrying.
