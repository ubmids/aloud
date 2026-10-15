# Owner to-do (private)

**Delete this file before the repository goes public or is shared with
reviewers** (`git rm docs/OWNER_TODO.md && git commit -m "docs: remove
checklist" && git push`). It is for Subomi, not for judges.

Deadline: Fri 23 Oct 2026, 12:00 PDT (19:00 UTC). Aim to submit Thu 22 Oct.

## Done on 15 Oct

- Tears of Steel re-described with its cast by Claude Haiku 4.5 ($0.14),
  13 cues refused in review, 45 shipped, 0.98 s overlap measured against the
  stems (docs/generation/TEARS_OF_STEEL.md). The local Qwen2.5-VL 7B run is
  kept for comparison, not shipped.
- The current app built, installed and run on the Vega Virtual Device;
  full screen fixed on the device; shelf density setting added.
- Video script, shot list, people plan and consent wording in docs/video/;
  pre-render tools (`docs/video/render.py`, `docs/video/record.py`).
- README, SUBMISSION, EVALUATION, DESCRIBERS, FRICTION_LOG (24 entries)
  quote the current build and track; rules re-checked.

## Left for you, in order

1. **Today/tomorrow: recruit the viewer** (docs/video/PEOPLE.md). Message
   your network and one organisation. Book a 30-minute slot by Tue 20 Oct.
2. **Mon 19 Oct, 9:00 PT: office hours #2.** Ask: "Our Fire TV demo plays
   a Creative Commons Blender film (Tears of Steel, CC BY 3.0, credited) to
   show audio description working; about 60% of the video shows the app
   playing it. Is that acceptable?" Keep the answer.
3. **Film your two to-camera lines and the voiceover** (docs/video/PEOPLE.md
   A1, A2; lines in docs/video/SCRIPT.md). Phone, quiet room, 20 minutes.
4. **Film the viewer session** with the two clips in docs/video/assets/
   (`tos-without.mp4`, `tos-with.mp4`), consent read and recorded first.
5. **Listen once with the Virtual Device GUI on** (`vega virtual-device start`
   without `--no-gui`): the shelf and settings should speak, and Menu should
   repeat the last description. If Menu does nothing, see MAC_CHECKLIST.
6. **Edit** in the order of docs/video/SCRIPT.md, under 2:59, using
   docs/video/assets/ (app shots and cards). Upload to YouTube, public,
   with the credits from docs/SUBMISSION.md in the description.
7. **Repo**: set About and topics (`gh repo edit ubmids/aloud --description
   "A Fire TV that tells you what is on screen, in the gaps between the
   dialogue" --add-topic fire-tv --add-topic vega-os --add-topic
   audio-description --add-topic accessibility`), delete this file, then
   either make `ubmids/aloud` and `ubmids/vega-described-track` public, or
   keep aloud private and add chris-trag knmeiss giolaq anishamalde
   mosesroth emersonsklar plus testing@devpost.com no earlier than 16 Oct.
   The Open Source mini needs vega-described-track public either way.
8. **Compute timings**: README "Where it goes" cites a shared 24-core Linux
   box for Sintel and Big Buck Bunny. If that box is Mark's, confirm citing
   it is fine or drop those two numbers (the Mac and Haiku figures are yours).
9. **Submit**: paste docs/SUBMISSION.md into Devpost, video link, Fire TV
   track + Open Source mini.
