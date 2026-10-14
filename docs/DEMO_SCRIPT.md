# Demo video: aloud (2:45, hard limit 2:59)

Amazon's advice for this hackathon: treat the video as a pitch, not a
tutorial; lead with the problem; make the required tool impossible to miss.
The required tool is **Vega OS on Fire TV**. It is named on screen by 0:16,
and every shot of the app is the Vega Virtual Device.

**The hero lands at 0:05**: a black screen, the film's own sound, and then
aloud's voice describing what you cannot see. At 0:12 the picture comes up on
the Vega Virtual Device with that description lit on screen.

Record at 1920x1080 with system audio. Everything aloud says in this video
comes from the shipped track, not a re-record. The quoted lines below are from
the track as it stands; if Tears of Steel is re-described (docs/DESCRIBERS.md),
replace them with what the new track says at the same times.

| time | section | length |
|---|---|---|
| 0:00 | cold open (the hero) | 20 s |
| 0:20 | remote, voice and picture in one flow | 30 s |
| 0:50 | a person | 30 s |
| 1:20 | how it works | 20 s |
| 1:40 | why this, when others exist | 25 s |
| 2:05 | every Vega app | 20 s |
| 2:25 | close and end card | 20 s |

## 0:00 to 0:20: the cold open

Record this on the Virtual Device itself, with the window covered by a black
card for the first 12 seconds, so the opening is the project running on the
device and not a composite.

| time | picture | sound |
|---|---|---|
| 0:00 | Black. Small white caption, bottom left: *"Tears of Steel, as a blind viewer hears it."* | Tears of Steel from 1:41 with narration **off**: score and effects, no words. |
| 0:05 | Still black. Caption: *"Now with aloud."* | Skip back to 1:41 with narration **on**. aloud at 1:41: *"A grey-haired person reads a newspaper while a soldier aims a rifle nearby."* |
| 0:12 | The black card fades off the Virtual Device window as aloud says *"Through a circular viewport, a large, steampunk-style airship hovers above a cityscape."* The airship is there, as described, with the line lit in the voice panel and its block sitting in a gap on the schedule strip. | The description ends inside its gap. |
| 0:16 | Title over the device picture: **aloud: films that describe themselves.** Under it: *Fire TV · Vega OS*. | *"Shouldn't you be down there?"* lands after the description has finished. |

Fallback, only if the device recording fails: `python3 -m aloud.clip
tears_of_steel_720p.mov out/ --at 101 --length 19 --reveal 8 --dest video/`
writes the same 19 seconds from the pipeline's own output. Cut to the device
by 0:16 either way.

## 0:20 to 0:50: remote, voice and picture in one flow

- Back to the shelf. **Right**: *"Sintel. Fantasy, 2010, 15 minutes. 41
  descriptions."* **Right**: *"Big Buck Bunny..."*. **Left** twice: *"Tears of
  Steel..."*. Each press cuts off the last. (Re-speak the shelf titles first:
  docs/OWNER_TODO.md.)
- Voiceover, one line: "Every title, and every setting, is read out in the
  voice that describes the film."
- **Down** to *Voice level*, select: *"Voice level, loud..."*. Up, select Tears
  of Steel. A description plays at Loud with the film dipping under it.
- **Narration off.** A few seconds of film. Press **Menu**: the film pauses,
  aloud repeats the most recent description, the film carries on. Voiceover:
  "Narration off for whoever doesn't need it. Menu repeats the last
  description for whoever does." Do not say Menu describes what is on screen
  now: it repeats the track.
- **Picture: Full screen**: the film fills the screen, the description shows
  as a caption. Voiceover: "And for everyone else on the sofa, it's just a
  film."
- Do not show Alexa voice commands unless "Alexa, pause" worked on the
  Virtual Device (MAC_CHECKLIST.md).

## 0:50 to 1:20: a person

**Best**: a blind or partially sighted viewer following thirty seconds of Big
Buck Bunny or Tears of Steel with aloud on, then one unscripted sentence. Ask
one checkable question afterwards ("what did the rabbit do to the
squirrels?") and keep the answer. Written consent to publish.

**Fallback**: you, eyes shut, with one line on who it is for; then the shelf
navigated with the screen covered. Do not imply a blind viewer has tested it.

## 1:20 to 1:40: how it works

On screen: the schedule strip, then the evaluation table from
docs/EVALUATION.md for three seconds (27.4 s down to 0.9 s). Voiceover, about
15 seconds:

"Ahead of time, a vision model looked at every silence where the picture had
changed and wrote one sentence sized to it. Each sentence is spoken and
measured before it is placed. Against the film's own production stems, this
track touches dialogue for under a second in twelve minutes."

## 1:40 to 2:05: why this, when others exist

"Prime Video uses AI to help its writers find the gaps. Services like 3Play
Media and ViddyScribe write AI description for publishers and for YouTube.
aloud is the television half: a Fire TV app a blind viewer runs alone, that
will not start a sentence the silence cannot hold. Made ahead of time, so a
person can review every line, and the TV does no AI work at all."

## 2:05 to 2:25: every Vega app

If the multi-TV sample PR is open (docs/UPSTREAM_PR.md): 8 to 10 seconds of
Amazon's react-native-multi-tv-app-sample on the Virtual Device speaking a
description. Voiceover: "The player is a library. Any Vega app can play a
described track." If the sample was not run on the device, show the library's
README for five seconds instead and say "a library, with a patch for Amazon's
sample", not "works in any app".

## 2:25 to 2:45: close

Back to black, Sintel at 4:44: *"Sintel runs up a broken stone staircase
toward distant ruins."* (checked against the frame at 4:46). Then: "Close your
eyes. aloud tells you what you are missing, in the silences between the
lines." End card: **aloud** · Fire TV · Vega OS · github.com/ubmids/aloud ·
*Any Vega app can play a described track: github.com/ubmids/vega-described-track*.

Credits on the end card and in the YouTube description: *Tears of Steel*,
(CC) Blender Foundation, mango.blender.org; *Sintel*, (c) copyright Blender
Foundation, durian.blender.org; *Big Buck Bunny*, (c) copyright 2008, Blender
Foundation, www.bigbuckbunny.org; all CC BY 3.0 (credit only the ones shown).

---

## Shot list

1. Virtual Device, window covered: Tears of Steel 1:41, narration off, then
   on; uncover at the airship.
2. Shelf: right, right, left, left, Voice level, select Tears of Steel.
3. Player: Loud dip, narration off, Menu, Full screen.
4. The person.
5. Schedule strip; EVALUATION.md table.
6. The multi-TV sample speaking a description (or the library README).
7. Black with Sintel at 4:44; end card.

## Do not

- Say "live" or "real time". The descriptions are made ahead of time; that is
  the strength.
- Say Menu "says what is on screen". It repeats the most recent description.
- Claim blind viewers have tested it, unless one has, on camera.
- Show any footage that is not Blender Foundation open film or your own.
- Run over 2:59.
