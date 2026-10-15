# Demo video: aloud (2:50, hard limit 2:59)

The pitch is **AI-enhanced viewing for everyone, with accessibility at its
core**: a television that tells you what is on screen whenever you are not
looking at it, built first for the people who never can. The required
platform, **Vega OS on Fire TV**, is on screen from 0:00 and every shot of the
app is the Vega Virtual Device running the build in this repository.

**The hero lands at 0:06.** Black screen, the film's own sound, then aloud's
voice describing what you cannot see; at 0:12 the picture fades up on the
Vega Virtual Device showing exactly what was described: a flying ship over
the city, in a rifle scope.

Who is in each part (details, consent and recruiting in
[PEOPLE.md](PEOPLE.md)):

- **[NO PERSON]**: pre-rendered, ready in `docs/video/assets/` (see
  [SHOTS.md](SHOTS.md)).
- **[SUBOMI]**: Subomi to camera, two short pieces.
- **[VIEWER]**: a blind or low-vision viewer, filmed with consent.
- **[VO]**: Subomi's voiceover, recorded on a phone in a quiet room.

| time | section | who | length |
|---|---|---|---|
| 0:00 | cold open: the hero | NO PERSON | 20 s |
| 0:20 | who made it, and why | SUBOMI | 7 s |
| 0:27 | for everyone: the remote, the voice, the picture | NO PERSON + VO | 38 s |
| 1:05 | a viewer who cannot see the screen | VIEWER | 30 s |
| 1:35 | how it works | NO PERSON + VO | 25 s |
| 2:00 | why this is new | NO PERSON + VO | 20 s |
| 2:20 | every Vega app | NO PERSON + VO | 13 s |
| 2:33 | close | SUBOMI, then NO PERSON | 17 s |

Quoted descriptions are the shipped Tears of Steel track
(`tv/src/data/films/tears-of-steel.json`); the times are film times.

---

## 0:00 to 0:20, cold open [NO PERSON]  (`assets/01-cold-open.mp4`)

| time | picture | sound |
|---|---|---|
| 0:00 | Black. Bottom left, `card-01-picture-off.png`: *Tears of Steel, with the picture off.* | Film from 1:30.5 at full volume: wind, a city, a rifle being readied. No words. |
| 0:06 | Still black. | aloud, at 1:36.5: *"Flying ship descends lower."* |
| 0:12 | aloud, at 1:42.4: *"The flying ship continues descending toward the residential buildings below."* As it speaks, the black fades off the Vega Virtual Device recording (full-screen picture): the flying ship hovering over the rooftops in a rifle scope, exactly as said, the sentence as a caption under it. | The film dips under the voice and comes back when it ends. |
| 0:16 | `card-02-title.png` over the device picture: **aloud**, *A Fire TV that tells you what is on screen, in the gaps between the dialogue*, *Fire TV · Vega OS*. | 1:51, the old man under the rifleman, Barley. *"Shouldn't you be down there?"* lands at 0:26.5, after the descriptions have finished. |

Pre-rendered by `docs/video/record.py` from a VVD screen recording, with the
app's own sound laid under it at the same timecode, because the Virtual
Device records picture only (FRICTION_LOG entry 19). Cut to 20 s; the asset
runs about 30 s so the edit has room.

## 0:20 to 0:27, who [SUBOMI]

> "I'm Subomi. I built aloud: a Fire TV that tells you what's on screen, in
> the gaps between the dialogue."

## 0:27 to 1:05, for everyone [NO PERSON + VO]  (`assets/02-shelf.mp4`, `03-player.mp4`, `card-03-who.png`; cards and the
lower third are the Signal set from `design/assets/`)

- 0:27, card *Cooking. Ironing. A toddler on your lap. A film in your second
  language. Eyes that are not what they were. Or no sight at all.* (4 s)
  **[VO]** "Most of us watch television without looking at it for half the
  film."
- 0:31, the shelf on the VVD. Right: *"Sintel. Fantasy, 2010, 15 minutes..."*
  Right: *"Big Buck Bunny..."*. Left, left: back to Tears of Steel. Down to
  *How much is said*: *"How much is said, everything."*
  **[VO]**, over the presses, ducked under the app: "Every title and every
  setting is read out by the voice that describes the film, so you can run
  it with your eyes shut."
- 0:45, select Tears of Steel. The player: a description plays, the film dips
  under it, the block lights on the schedule strip.
- 0:52, *Narration off* (the film plays on, no descriptions), then **Menu**: the film pauses, aloud says the
  latest description again, the film carries on. **[VO]** "Narration off for
  whoever doesn't need it. One button repeats the last description for
  whoever does."
- 0:59, *Picture: Full screen*: the film fills the screen, the description
  as a caption. **[VO]** "And for everyone else on the sofa, it's just a
  film."

## 1:05 to 1:35, a viewer [VIEWER]

Recorded per [PEOPLE.md](PEOPLE.md). In the cut: lower third *[first name or
"A viewer"], [blind / low vision]*; 4 to 6 s of their answer after the scene
**without** aloud; 6 to 10 s after the same scene **with** aloud; their one
unscripted sentence. Their words captioned on screen, large.

**Fallback if nobody is found by Wed 21 Oct [SUBOMI]:** Subomi in a sleep
mask on the sofa, remote in hand, the VVD on the TV behind. Caption: *"I can
see. 2.2 billion people have some form of vision impairment. This is the
same scene with the picture taken away."* Then 15 s of `tos-with.mp4` over
black. Claim nothing about blind viewers.

## 1:35 to 2:00, how it works [NO PERSON + VO]  (`card-04-how.png`, `assets/04-strip.mp4`, `docs/schedule.svg`)

**[VO]**, about 20 s:

> "Ahead of time, aloud finds every silence in the dialogue, listening three
> ways. A vision model looks at each silence where the picture has changed
> and writes one sentence sized to it. Each sentence is spoken and measured
> before it is placed. Against the film's own production stems, the whole
> track touches dialogue for under a second, in twelve minutes."

Picture: the schedule strip on the VVD, then `docs/schedule.svg` full screen
for 3 s, then the card.

## 2:00 to 2:20, why this is new [NO PERSON + VO]

> "Prime Video uses AI to help its writers find the gaps. Services like
> 3Play Media write AI description for publishers. aloud is the television
> half: a Fire TV app a blind viewer can run alone, that will not start a
> sentence the silence cannot hold. Made ahead of time, so a person can check
> every line, and the TV does no AI work at all."

Picture: the full-screen player with captions, Sintel or Big Buck Bunny.

## 2:20 to 2:33, every Vega app [NO PERSON + VO]  (`card-05-library.png`)

> "The player is a library. Any Vega app can play a described track."

Picture: the card, then the `vega-described-track` README for 4 s. If the
multi-TV sample has been run with the patch on the VVD, show that instead
(see docs/UPSTREAM_PR.md); otherwise do not say "works in any app".

## 2:33 to 2:50, close [SUBOMI, then NO PERSON]  (`card-06-end.png`)

**[SUBOMI]**

> "Look away, close your eyes, or never see the screen at all. aloud keeps
> you in the film."

End card (5 s): **aloud** · Fire TV · Vega OS · github.com/ubmids/aloud ·
*Any Vega app can play a described track: github.com/ubmids/vega-described-track*
· film credits.

---

## Rules for the edit

- Under 2:59 total. Export 1080p, upload to YouTube as public (or unlisted is
  not enough: the rules say publicly visible), English captions on.
- YouTube description: one line pitch, the repo link, and the credits from
  docs/SUBMISSION.md ("Credits and licences").
- Do not say "live" or "real time"; do not say Menu "says what is on screen
  now" (it repeats the latest description); do not claim a blind viewer
  tested it unless segment [VIEWER] was filmed.
- Do not show Alexa voice commands (untested on the device).
- Film footage is Blender Foundation open film only, credited, and only as
  much as the app needs to show itself working. Ask about it at office hours
  #2 (Mon 19 Oct, 9:00 PT) and keep the answer.
