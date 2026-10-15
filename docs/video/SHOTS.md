# Shot list and pre-rendered assets

Everything in this list that does not need a person is rendered and lives in
`docs/video/assets/` (kept out of git: films and recordings are large and the
films are third-party; rebuild with the commands below). Every app shot is a
screen recording of the Vega Virtual Device (`vega virtual-device start
--no-gui`, recorded through the emulator console), with the app's sound laid
under it at the same timecode from the files in the app package
(`render.py lay`; the Virtual Device records picture only, FRICTION_LOG
entry 19).

| # | asset | used at | what it shows | person? |
|---|---|---|---|---|
| 1 | `01-cold-open.mp4` | 0:00 | VVD, Tears of Steel from 1:30.5 in full-screen picture; black for 12.5 s with the film's sound and the first two descriptions, then the picture fades up on the flying ship in the rifle scope | no |
| 2 | `02-shelf.mp4` | 0:31 | VVD shelf: right, right, left, left (each title read out), down to the settings (each read out) | no |
| 3 | `03-player.mp4` | 0:45 | VVD player, Tears of Steel with the voice panel and schedule strip: a description plays and the film dips; Narration off; Menu repeats the latest description; Picture: Full screen | no |
| 4 | (from `03-player.mp4`) | 1:35 | the schedule strip under the film while a description fills its gap; crop it in the edit | no |
| 5 | `card-01` to `card-06`, `lower-third.png`, `caption.png`, `thumbnail-*.png` | throughout, YouTube thumbnail | the Signal cards from `design/assets/` (designed and rendered by the design pass; `render.py cards` copies them here) | no |
| 6 | `tos-without.mp4`, `tos-with.mp4` | viewer session | Tears of Steel 1:31 to 2:10 over black: the film's own sound, then with aloud | no (played to the viewer) |
| 7 | `design/assets/gallery/*.png` | Devpost gallery, README | VVD screenshots of the Signal build at 1920x1080 (design pass) | no |
| 8 | Subomi to camera, A1 and A2 | 0:20, 2:33 | see PEOPLE.md | **Subomi** |
| 9 | Voiceover | 0:27 to 2:33 | lines in SCRIPT.md | **Subomi** (voice) |
| 10 | The viewer session | 1:05 | see PEOPLE.md | **blind or low-vision viewer** |

## Rebuilding the assets

```bash
python3 docs/video/render.py cards docs/video/assets
python3 docs/video/render.py viewer path/to/tears_of_steel_720p.mov docs/video/assets
# the app shots, recorded on a running Virtual Device with the build installed:
python3 docs/video/record.py path/to/tears_of_steel_720p.mov docs/video/assets
#   (or --only cold / shelf / player; each relaunches the app first)
# re-lay the sound under an existing recording from its plan:
python3 docs/video/render.py lay docs/video/assets/rec-cold.webm docs/video/plans/01-cold-open.json docs/video/assets/01-cold-open.mp4
```

`record.py` writes a plan per shot to `docs/video/plans/`: which moment of
the film was on screen (measured by matching recording frames to the film),
the recorder's clock correction (its timestamps run about 0.8 of real time
under a moving picture, while the device plays in real time), and which menu
clip was spoken when. Plans contain no sound of their own: every sound in an
asset is the film or a file from the app package.

## Recording the Virtual Device

```bash
vega virtual-device start --no-gui
vega run-app tv/build/aarch64-release/aloud_aarch64.vpkg
# emulator console: port 5554, token in ~/.emulator_console_auth_token
#   auth <token>
#   screenrecord start --fps 30 /abs/path/rec.webm      (max 180 s)
#   screenrecord stop
#   screenrecord screenshot /abs/dir
# remote keys:
vega device run-cmd -c 'inputd-cli button_press KEY_RIGHT'   # LEFT, UP, DOWN, ENTER, BACK, MENU
vega virtual-device stop && pkill -f "vega-sdk.*crashpad_handler"
```

Record with the GUI off; the GUI device takes the Mac's audio output.
