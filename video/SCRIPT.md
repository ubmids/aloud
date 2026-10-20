# aloud: what you say (8 short lines, about 75 seconds in total)

The app does most of the talking: its own voice describes the film. You
only add short lines between the shots. Speak slowly and plainly, like
you're explaining it to one friend. Record each line two or three times
in one memo, then keep the clean take.

Say "aloud" like the word: "a-LOUD".

The file names matter. `docs/video/cut.py` picks each memo up by its name.
These lines are also in `docs/video/cut.py` (LINES). Keep the two the same.

---

[SCREEN, 0:00 to 0:20: black screen, the film's sound, aloud's voice describing a flying ship. Then the picture fades up on that ship. **You say nothing here.**]

### 1. `n-who` (about 6 s)
[SCREEN: aloud title card over the blurred TV shelf]

> I'm Subomi. I built aloud.
> A Fire TV app that tells you what's on screen,
> in the gaps between the dialogue.

### 2. `n-everyone` (about 3 s)
[SCREEN: card. "Cooking. Ironing. A toddler on your lap. Or no sight at all."]

> Most of us watch TV without looking at it half the time.

### 3. `n-shelf` (about 5 s)
[SCREEN: the TV shelf, Tears of Steel focused]

> Every title and every setting is read out loud,
> so you can use it with your eyes shut.

[SCREEN: the shelf moves right and left, and the app reads Sintel and Big Buck Bunny. **You say nothing.**]

[SCREEN: the player. A description plays, the film dips under it, then narration goes off. **You say nothing for the first 22 seconds.**]

### 4. `n-player` (about 6 s, must be under 8 s)
[SCREEN: "Narration: Off" is highlighted and the film plays on its own]

> Narration off, for whoever doesn't need it.
> One button repeats the last description, for whoever does.

[SCREEN: Menu pressed. The film pauses and aloud repeats its last line. **You say nothing.**]

### 5. `n-how` (about 15 s)
[SCREEN: card. "Ahead of time, not live."]

> Ahead of time, aloud finds every silence in the dialogue.
> A vision model looks at each one,
> and writes one sentence that fits it.
> Each sentence is spoken and measured before it goes in.
> Across the whole film, the voice touches dialogue for under a second.

### 6. `n-new` (about 13 s)
[SCREEN: the film full screen, the flying ship]

> Prime Video uses AI to help its writers find the gaps.
> aloud is the TV half.
> An app a blind viewer can run alone,
> that never starts a sentence the silence can't hold.
> It's all made ahead of time, so a person can check every line.

### 7. `n-library` (about 4 s)
[SCREEN: card. "Any Vega app can play a described track."]

> The player is a library.
> Any Vega app can play a described track.

### 8. `n-close` (about 5 s)
[SCREEN: end card, github.com/ubmids/aloud]

> Look away, close your eyes, or never see the screen at all.
> aloud keeps you in the film.

---

## What not to say (from the rules notes in docs/video/SCRIPT.md)

- Not "live" or "real time".
- Not that Menu "says what's on screen now". It repeats the latest description.
- Not that a blind viewer tested it. Nobody has yet.
- Nothing about Alexa voice commands. They're untested on the device.

## No-voice fallback (captions)

If you record nothing, `cut.py` puts each line above on screen as a caption
box, bottom left (top left on the title card). It holds each one for its
reading time. This version is already rendered:
`~/Desktop/hackathons/aloud-video/aloud-demo.mp4` (2:48).

| shot | caption on screen |
|---|---|
| title card | I'm Subomi. I built aloud. A Fire TV app that tells you what's on screen, in the gaps between the dialogue. |
| "Cooking. Ironing." card | Most of us watch TV without looking at it half the time. |
| shelf still | Every title and every setting is read out loud, so you can use it with your eyes shut. |
| player, narration off | Narration off, for whoever doesn't need it. One button repeats the last description, for whoever does. |
| "Ahead of time" card | Ahead of time, aloud finds every silence in the dialogue. A vision model looks at each one, and writes one sentence that fits it. Each sentence is spoken and measured before it goes in. Across the whole film, the voice touches dialogue for under a second. |
| full-screen film | Prime Video uses AI to help its writers find the gaps. aloud is the TV half. An app a blind viewer can run alone, that never starts a sentence the silence can't hold. It's all made ahead of time, so a person can check every line. |
| library card | The player is a library. Any Vega app can play a described track. |
| end card | Look away, close your eyes, or never see the screen at all. aloud keeps you in the film. |

You can mix the two. Any memo that exists is used, and every missing line
stays a caption.
