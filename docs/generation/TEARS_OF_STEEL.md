# Tears of Steel: how the shipped description track was made (15 Oct 2026)

Tears of Steel is the film the demo video is built on, so it is the one
track a judge will certainly hear. Until 15 October it was the oldest track on
the shelf: written by Qwen3-VL 4B on a CPU before the title had a cast list,
so for twelve minutes it said "a grey-haired man" and "a man with a mechanical
eye" while the dialogue said Thom and Captain. This note records how it was
re-described, what was tried first, and what was refused.

## Result

| | before (14 Oct) | now |
|---|---|---|
| describer | Qwen3-VL 4B, llama.cpp on CPU | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`), OpenAI-compatible endpoint |
| cast list | none | Thom, Celia, Barley, the Captain, plus a rule for the machines (`aloud/films.py`) |
| descriptions written | 46, 42 after the gate | 58 |
| refused in review | 0 | 13 (listed below) |
| shipped | 42, 157.6 s of speech | **45, 134.8 s of speech** |
| overlap with dialogue, against the production stems | 0.9 s, 5 touches | **0.98 s, 6 touches**, each under 0.4 s, none on a captioned line |
| voice | Kokoro 82M (af_heart) | Kokoro 82M (af_heart) |

The overlap is measured by `python3 -m aloud.evaluate` against the film's own
dialogue and music-and-effects stems, as in docs/EVALUATION.md. The six
touches are at 63.4 s (0.09), 248.4 s (0.06), 431.8 s (0.22), 479.0 s (0.37),
539.5 s (0.02) and 567.4 s (0.22): each is the tail of a line a few tenths of
a second past where the caption file says it ends, or, at 479 s, the
uncaptioned battle the old track also touched.

## What was tried first: an open model on this Mac

The first run used **Qwen2.5-VL 7B through Ollama** on the M2 Pro laptop
(16 GB), with no key: about 35 seconds a request, 75 minutes for the film.
Its full output is in `tos-qwen2.5vl-7b-local.json`. It was not good enough
to ship, for three reasons a listener would notice:

1. **It put the giant robot everywhere.** The first cast list said that forty
   years later Celia *is* the giant robot. From then on the flying ship, a
   technician's console and a man adjusting his eyepiece were all "the giant
   robot": 16 of its 35 descriptions mention it.
   - 1:48, the hero moment, where a flying ship hovers over the city in a rifle
     scope: *"The giant robot moves slowly, emitting smoke."*
   - 6:37, the curly-haired technician staring at a screen: *"The giant
     robot's arm moves closer to Thom's face."*
2. **It said nothing.** 2:54: *"The room is dimly lit."* 2:39: *"The old man
   stands."*
3. **It wrote the same sentence twice.** 1:34 and 1:41: *"The man aims the
   rifle."*, *"The man aims the rifle, focusing on the target."*

Claude Haiku 4.5 made the same robot mistake with the first cast list, so the
cast list was at fault as much as the model. It was rewritten
(`0424faf`) to name the machines by what they look like ("a flying ship";
"the giant robot" only for a huge humanoid robot plainly in the frame). The
local model was not re-run with the new list; that would be the fair
comparison, and it costs nothing but 75 minutes of laptop time
(see "Regenerating", below).

## The paid pass

One full pass with Claude Haiku 4.5, through an OpenAI-compatible relay, with
frames sent at 512 pixels wide (`ALOUD_FRAME_MAX=512`) and only the frames the
gaps need (two per gap at most, the second a second later in the same shot).
Every answer is cached beside the track (`described.cache.json`), so a re-run
pays nothing.

| | requests | cost |
|---|---|---|
| spot check on 2 frames | 2 | $0.002 |
| full pass, first cast list (discarded, robot everywhere) | 139 | $0.143 |
| spot check of the corrected cast on 7 frames | 7 | $0.007 |
| full pass, corrected cast list (shipped) | 133 | $0.142 |
| **total** | **281** | **$0.29** |

About $0.001 a request, 7.5 minutes for the film. Describing a back catalogue
of feature films at this rate costs about $1 a title.

Sample lines from the shipped track (film time):

| time | description |
|---|---|
| 0:45 | On screen: 40 YEARS LATER. |
| 1:03 | A human brain sits on a white platform surrounded by glowing pink circular light rings. |
| 1:09 | The flying ship hovers above the sprawling city below. |
| 1:24 | Barley peers through rifle scope. |
| 1:42 | The flying ship continues descending toward the residential buildings below. |
| 2:01 | The old man lies beneath metal framework as Barley aims downward. |
| 2:18 | The old man stands in a high rooftop shelter as the flying ship looms outside the windows beyond. |
| 5:10 | Thom stands facing a woman with light brown hair in a city square. |
| 6:51 | The Captain's mechanical eyepiece glows red as a woman watches from behind him. |
| 9:03 | The old man stands before the giant robot's massive torso, reaching toward its metal chest as the fist descends toward him. |

## Refused in review (13)

Each was checked against the frame at its start and removed with
`python3 -m aloud.publish --regate --id tears-of-steel --drop START`. Their
gaps are silent; nothing was written by hand.

| time | description | why |
|---|---|---|
| 4:24.8 | Stone pillar stands in overgrown courtyard. | young Thom is on the bridge with his phone |
| 5:05.4 | The Captain manipulates glowing holographic controls with his hands. | it is the curly-haired technician, not the Captain |
| 5:50.4 | Flying ship fires pink energy beams. | technicians in a pink holographic room; no ship |
| 6:33.4 | Young man holds gun to mouth. | a robotic hand at his face; "gun" misleads |
| 7:19.0 | Flying ship descends. | a robot on a clock tower |
| 7:24.8 | Hands in dark sleeves lower the flying ship onto a detailed miniature model ... | a young man in white holds a robotic device |
| 7:48.3 | Thom, a young man with light brown hair in a cream shirt, sits at controls ... | not Thom |
| 8:28.5 | Man's face bleeds from impact. | the Captain's red eyepiece, not blood |
| 9:34.8 | The old man gestures toward soldiers. | he gestures at the robot wreckage |
| 9:49.0, 9:56.0, 10:01.1, 10:21.5 | four sentences about "the giant robot" | the end credits' line-art animation, narrated as story |

Kept with a known weakness: the first description, at 0:11.6, *"Bright
industrial lights blaze intensely within a metal framework structure
overhead."*, is a fair account of the frame but does not say they are rocket
engines firing; the old track did.

## Regenerating

Hosted (any OpenAI-compatible endpoint; the shipped run):

```bash
export ALOUD_VISION=openai ALOUD_LLM_BASE_URL=... ALOUD_LLM_API_KEY=... \
       ALOUD_LLM_MODEL=claude-haiku-4-5-20251001 ALOUD_LLM_PROVIDER=hosted \
       ALOUD_FRAME_MAX=512 ALOUD_TTS=kokoro
python3 -m aloud tears_of_steel_720p.mov --captions TOS-en.srt --out out/ \
       --cast-of tears-of-steel --no-mix
python3 -m aloud.publish out --id tears-of-steel
```

Local, no key (Ollama):

```bash
ollama pull qwen2.5vl:7b
export ALOUD_VISION=openai ALOUD_LLM_BASE_URL=http://localhost:11434/v1 \
       ALOUD_LLM_API_KEY=unused ALOUD_LLM_MODEL=qwen2.5vl:7b \
       ALOUD_LLM_PROVIDER="local, Ollama" ALOUD_LLM_TIMEOUT=600 ALOUD_FRAME_MAX=512
# then the same two commands
```

Switching between them is the four `ALOUD_LLM_*` variables and nothing else.

## Files

- `tos-claude-haiku-4.5-raw.json`: the shipped run before review (58 cues).
- `tos-qwen2.5vl-7b-local.json`: the local run (35 cues), not shipped.
- `tos-qwen3-vl-4b-previous.json`: the track shipped until 15 October.
- The shipped track: `tv/src/data/films/tears-of-steel.json`.
