# Owner to-do (private)

**Delete this file before the repository goes public or is shared with
reviewers** (`git rm docs/OWNER_TODO.md && git commit -m "docs: remove
checklist" && git push`). It is for Subomi, not for judges.

Deadline: Fri 23 Oct 2026, 12:00 PDT (19:00 UTC).

## Done on 14 Oct (branch `first-place`)

- `778b6e8` The sentence gate now refuses blur, off-camera and crew-credit
  cues. Ten shipped cues are gone, and so is the wrong Sintel 5:28 cue,
  dropped by reviewer refusal. Their gaps are silent, with no hand-written
  replacements. The counts are now Tears of Steel 42, Sintel 41, Big Buck
  Bunny 47 and the trailer 4. The overlap figure is unchanged (0.9 s).
- `0b1e20f` Tears of Steel has a cast list (Thom, Celia, Barley, the
  Captain). There is a continuity pass behind `ALOUD_CONTINUITY=1`, tested
  with fakes in `tests/test_continuity.py`.
- `705393b` Copy changes:
  - Menu is described exactly: it repeats the latest description.
  - Removed "close your eyes and you can still follow", "Native Vega, end to
    end", "gives any player" and "PENDING" notes.
  - Positioning against 3Play, Verbit, Audible Sight, ViddyScribe and
    YouDescribe.
  - Impact now covers "every Vega app".
- `adc286a` The demo script runs 2:45 with the hero at 0:05, recorded on
  the VVD. Added the regeneration command (docs/DESCRIBERS.md) and the
  upstream PR text (docs/UPSTREAM_PR.md).

## Left for you, in order

1. **Re-speak the shelf titles** (the counts changed; the JSON says 42/41/47,
   the audio still says 45/47/48). On the Mac, with Kokoro (not `say`):
   ```bash
   pip install kokoro-onnx soundfile
   mkdir -p ~/.cache/aloud/kokoro && cd ~/.cache/aloud/kokoro
   curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx
   curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
   cd -   # back to the repo
   for id in tears-of-steel sintel big-buck-bunny; do
     ALOUD_TTS=kokoro python3 -m aloud.publish --id $id --announce; done
   git add tv/assets && git commit -m "shelf: re-speak titles with the new counts" && git push
   ```
   Skip `tears-of-steel` here if you do step 3, which re-speaks it anyway.
2. **Check the Tears of Steel cast against the picture** before step 3. In
   `aloud/films.py` `TOS_CAST`, check that Barley is the curly-haired man with
   glasses at the console (around 1:20 to 2:10), and that the Captain is the
   man with the mechanical eye (around 6:50 and 9:25). Fix either line if
   it is wrong.
3. **Once a vision-model key arrives**, re-describe Tears of Steel with its
   cast and run the continuity pass: follow "Tears of Steel with its cast, and
   the continuity pass" in docs/DESCRIBERS.md. The command is
   `ALOUD_TTS=kokoro GEMINI_API_KEY=... ALOUD_CONTINUITY=1 python3 -m
   aloud.films build --only tears-of-steel`. Plug the laptop in first. Fetch
   the stems (two files, 211 MB each, URLs in `aloud/films.py`) and re-run
   `aloud.evaluate`. Then:
   - Compare five cues by ear against the old track (`git show
     HEAD~:tv/src/data/films/tears-of-steel.json`) and keep the better one.
   - If you keep the new one, update the counts, the 0.9 s figure and the
     describer name in README.md, docs/SUBMISSION.md and docs/EVALUATION.md.
   - Delete the sentence saying Tears of Steel's track predates its cast
     list (README "A track a person can check", SUBMISSION "Reviewable").
   - Update the quoted lines in docs/DEMO_SCRIPT.md.
4. **VVD run**: walk docs/MAC_CHECKLIST.md on the current build. Then
   docs/SUBMISSION.md can say the current app ran on the VVD; today it only
   says the September version did.
5. **Multi-TV sample**:
   - Fork AmazonAppDev/react-native-multi-tv-app-sample.
   - Apply `examples/react-native-multi-tv-app-sample.patch` from
     vega-described-track.
   - Run it on the VVD with one `.ad.vtt` beside a stream and record 10
     seconds.
   - Fill in "Tested" in docs/UPSTREAM_PR.md, then open the PR under your
     name only.
6. **Recruit a blind or partially sighted viewer** for the 0:50 segment
   (written consent). If nobody is found, use the fallback and claim nothing.
7. **Record** per docs/DEMO_SCRIPT.md. Upload it publicly to YouTube under
   2:59, with the Blender credits in the description.
8. **Repo housekeeping**:
   - Merge `first-place` into `master`, because master's README still says
     "live": `git checkout master && git merge --ff-only first-place || git
     merge first-place; git push origin master`. Or set the default branch
     to `first-place`.
   - Set the About text and topics: `gh repo edit ubmids/aloud --description
     "Films that describe themselves, on Fire TV (Vega OS)" --add-topic
     fire-tv --add-topic vega-os --add-topic audio-description --add-topic
     accessibility`.
   - Delete this file.
   - Run a secret sweep, then make `ubmids/aloud` and
     `ubmids/vega-described-track` public.
   - Or keep them private and add `chris-trag knmeiss giolaq anishamalde
     mosesroth emersonsklar` (`gh api -X PUT
     repos/ubmids/aloud/collaborators/$u -f permission=pull`) plus
     testing@devpost.com, no earlier than 16 Oct.
9. **Ask about Creative Commons footage** at office hours #2 (Mon 19 Oct,
   9:00 PT) and keep the answer.
10. **Compute timings**: README "Where it goes" cites "a shared 24-core Linux
   box". If that box is Mark's, confirm that citing it is fine, or re-time on
   your own machine.
11. **Paste the copy** from docs/SUBMISSION.md, including Product Feedback and
   feature requests, then submit before 23 Oct, 19:00 UTC.

## Not done, and why

- Menu still repeats the latest description. It does not describe the
  current shot: that needs a dense per-shot track, and so model time. The
  copy now says exactly what it does.
- Jest was not run, because `tv/node_modules` is absent and installing it is
  a large download. No TypeScript was changed. The Python suites I touched
  pass: test_gate, test_publish, test_continuity, test_film and
  test_caption. test_pipeline is untouched; it imports only budget, gaps
  and synth.
- The vega-described-track README was not edited, because this task pushes
  only to aloud. It already says that the patch "has not yet been built or
  run on a Vega device".
