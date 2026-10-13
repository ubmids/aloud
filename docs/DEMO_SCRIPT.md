# Demo video: aloud (under 3:00)

Amazon's own advice for this hackathon: treat the video as a pitch, not a
tutorial; lead with the problem; make the required tool impossible to miss.
The required tool is **Vega OS on Fire TV**: it is named on screen in the first
20 seconds and the whole middle of the video is the Vega Virtual Device.

**The hero lands at 0:08**: a black screen, the film's own sound, and then
aloud's voice describing what you cannot see. The picture comes up at 0:12 on
the Vega Virtual Device with that description lit on screen.

Record at 1920x1080 with system audio. Everything spoken by aloud in this video
is the shipped track, not a re-record.

---

## 0:00 to 0:20: the cold open (the hero)

| time | picture | sound |
|---|---|---|
| 0:00 | Black. White caption, small, bottom left: *"Tears of Steel, as a blind viewer hears it."* | `without.mp4`, first 5 seconds: the film's score and effects, no words. A blind viewer has no idea what is happening. |
| 0:05 | Still black. Caption changes to: *"Now with aloud."* | `hero.mp4` from its start: the same moment, and aloud's voice at 0:05: *"A grey-haired person reads a newspaper while a soldier aims a rifle nearby."* |
| 0:12 | Still black for one beat, then the picture fades up as aloud says: *"Through a circular viewport, a large, steampunk-style airship hovers above a cityscape."* The airship is there, in its circular viewport, exactly as described. | The description ends; the film carries on. |
| 0:16 | Cut to the **Vega Virtual Device**, Tears of Steel playing in aloud at about 1:48, the same description lit in the voice panel and sitting in a gap on the schedule strip. Title card over it: **aloud: films that describe themselves.** Under it: *Fire TV · Vega OS*. | At 0:21 the next line, *"Shouldn't you be down there?"*, lands after the description has finished: aloud never talks over it. |

Both clips are already cut, from the pipeline's own output (the voice in them is
the voice in the app):

```bash
python3 -m aloud.clip tears_of_steel_720p.mov out/ --at 101 --length 19 --reveal 8 --dest video/
```

writes `video/without.mp4` (black, film sound, 1:41 to 2:00 of the film) and
`video/hero.mp4` (black, described, the picture fading up at 1:49). The 0:16
shot must be the Virtual Device itself, so Stage One sees Vega OS inside the
first 20 seconds.

## 0:20 to 0:50: remote, voice and narration in one flow

Press Back to the shelf. On screen: the shelf on the Vega Virtual Device.

- Press **right**: *"Sintel. Fantasy, 2010, 15 minutes. 49 descriptions."* is
  heard. Press **left**: *"Tears of Steel..."*. Each press cuts off the last.
- Say (voiceover, short): "Every title is read out as you reach it, in the same
  voice that will describe the film. If VoiceView is on, aloud steps aside."
- Press **down** to *Voice level*, select twice: Normal, Loud. Up, select Tears
  of Steel.
- In the player: show a description at Loud with the film dipping under it.
- Turn **Narration off**, let a few seconds of film play, then press **Menu**:
  the film pauses, aloud says what is on screen, the film carries on. Voiceover
  (short): "Narration off for whoever doesn't need it. One button for whoever
  does." This is the multi-modal beat: remote, voice and picture in one flow.
- Narration back on, skip back ten seconds and let a description fire again.
- If "Alexa, pause" worked on the Virtual Device (see MAC_CHECKLIST), do it
  here. If not, do not show it.

## 0:50 to 1:20: a person

**Best**: a blind or partially sighted viewer, eyes closed or not, watching
thirty seconds with aloud on, then one sentence in their own words. Get written
consent to publish.

**Fallback**: you, eyes shut, with a line about who you built it for and why;
then the shelf being navigated with the screen covered.

## 1:20 to 1:50: how it works

Over the player, with the schedule strip visible:

"A vision model watched every shot of this film, ahead of time, not live. It
saw two frames of each shot and what it had already said, and wrote one
sentence sized to the silence it had to fit in. These were written by an open
model running on an ordinary CPU; Gemini or any hosted model is one setting.
Each sentence is spoken and measured before it is placed, and the track refuses
to be written if any of them would leave its gap."

On screen briefly: `docs/EVALUATION.md`'s table: 27.4 s of dialogue inside the
hand-built detector's gaps, 0.9 s with all three ears, and the shipped track's
0.9 s, measured against the film's own production stems.

## 1:50 to 2:20: why this, and why not Prime Video's

"Prime Video already uses AI to find gaps in the dialogue, so its writers can
work faster. A person still writes every line, which is why most film has no
description at all. aloud writes it, places it and plays it, for the titles
nobody will pay a describer for: free streaming channels, archives, independent
film. And it is a standard timed track, so a person can still check it before
it airs, and the TV itself does no AI work."

"It is for blind viewers first. It is also for anyone watching without
looking: the cook, the parent, the viewer whose eyesight is going."

## 2:20 to 2:45: close

Back to black, with a description playing over it (any vivid cue from Sintel).
Then: "Close your eyes. aloud tells you what you are missing, and never talks
over anyone." End card: **aloud** · Fire TV · Vega OS · github.com/ubmids/aloud.

Credits on the end card and in the YouTube description: *Tears of Steel*,
(CC) Blender Foundation, mango.blender.org; *Sintel*, (c) copyright Blender
Foundation, durian.blender.org; both CC BY 3.0.

---

## Shot list

1. Cold open: `without.mp4`, then `hero.mp4` (or re-record the same seconds on
   the Virtual Device with the window covered).
2. Virtual Device, Tears of Steel in the player at 1:48 (seek there with the
   skip buttons, or play from 1:38), the airship description lit.
3. Shelf: right, left, settings, select. Audio on.
4. Player: Loud level dip, play/pause, skip back, Back to shelf.
5. The person.
6. The evaluation table (screen capture of EVALUATION.md is fine).
7. Black with a Sintel description; end card.

## Do not

- Say "live" or "real time". The descriptions are made ahead of time; that is
  the strength.
- Show any footage that is not Blender Foundation open film or your own.
- Run over 2:59.
