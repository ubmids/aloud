# Describers: who writes the descriptions

aloud's pipeline asks a vision-language model to describe one moment of film
at a time, with a word budget set by the silence it has to fit in. The model is
a provider chosen by the environment. Every provider gets the same brief
(`aloud/caption.py`), the same cleaning, and the same refusal of sentences that
are about the film rather than of it ("Text appears on screen."), so changing
the model changes the writing and nothing else.

| provider | set | notes |
|---|---|---|
| Google Gemini | `GEMINI_API_KEY` (optional `ALOUD_GEMINI_MODEL`, default `gemini-2.5-flash`) | REST `generateContent`; key in a header, never the URL |
| Any OpenAI-compatible endpoint | `ALOUD_LLM_BASE_URL`, `ALOUD_LLM_API_KEY`, `ALOUD_LLM_MODEL` | OpenAI, OpenRouter, Together, vLLM, LM Studio... |
| Local open model on the CPU | `ALOUD_LOCAL_VLM_URL` (optional `ALOUD_LOCAL_VLM_MODEL`) | llama.cpp `llama-server`; no key, no GPU |
| Stub | `ALOUD_VISION=stub` | obviously not looking, for testing the plumbing |

With nothing forced, the first configured wins, hosted before local. With
`ALOUD_VISION=gemini|openai|local|stub` the choice is obeyed or refused, never
swapped for something else.

## What shipped in the app, and how it was made

The tracks in `tv/src/data/films/` were written by **Qwen3-VL 4B Instruct**
(Q4_K_M GGUF, about 3 GB with its vision projector) running on a CPU through
llama.cpp, on a shared 24-core Linux box with no GPU. Sintel and Big Buck
Bunny were re-described on 14 October 2026 with the sentence gate and each
title's cast list (`cast` in `aloud/films.py`): 33 and 14 minutes wall clock
with 8 model threads while other jobs ran, roughly 15 to 20 seconds per
request at that load. Big Buck Bunny names only Bunny: the film has no
dialogue, and naming its three bullies from the credits led the model to put
the wrong name on the wrong animal. One Big Buck Bunny cue was refused in
review ("The grey-haired man holds the red squirrel...", in a film with no
people; `python3 -m aloud.publish --regate --id big-buck-bunny --drop 458.292`).
Tears of Steel and the trailer keep their earlier tracks; Tears of Steel had
one cue taken off by the gate (`python3 -m aloud.publish --regate`). Every track file names its describer
and its voice, and the app shows both on the title's panel.

```bash
# the model (about 2.5GB) and its vision projector (about 0.45GB)
huggingface-cli download Qwen/Qwen3-VL-4B-Instruct-GGUF \
  Qwen3VL-4B-Instruct-Q4_K_M.gguf mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf --local-dir models

# llama.cpp's CPU build, from github.com/ggml-org/llama.cpp/releases
llama-server -m models/Qwen3VL-4B-Instruct-Q4_K_M.gguf \
  --mmproj models/mmproj-Qwen3VL-4B-Instruct-Q8_0.gguf \
  --port 8181 -t 10 -c 4096 -np 1 -ngl 0 -lm none --image-max-tokens 1024 \
  --cache-ram 0 --alias qwen3-vl-4b

export ALOUD_LOCAL_VLM_URL=http://127.0.0.1:8181/v1
```

The 8B model (`Qwen/Qwen3-VL-8B-Instruct-GGUF`, `--alias qwen3-vl-8b`, and
`ALOUD_LOCAL_VLM_MODEL=qwen3-vl-8b`) writes slightly richer sentences and was
used for the first runs, but at about 6 GB resident it was more than this
shared machine could spare while other jobs ran, and a run was killed partway
through the first full film. The 4B model fits comfortably.

One slot and a 4k context are deliberate for the same reason: the default of
four slots at 8k reserves several gigabytes of KV cache. `--cache-ram 0` turns
off the server's prompt cache, which by default keeps up to 8 GiB of old
prompts in memory; every request here carries a new image, so it never hits,
and on this machine it grew until the out-of-memory killer took the server
partway through a film. `-lm none` loads the weights once instead of mapping
them and keeping a repacked copy beside the map.

## Regenerating everything with a hosted model

```bash
export GEMINI_API_KEY=...          # or ALOUD_LLM_BASE_URL / _API_KEY / _MODEL
python3 -m aloud.films build       # fetch, describe, publish every title
cd tv && npm run build             # then install on the Vega Virtual Device
```

`build` downloads each film and its captions from download.blender.org, runs the
pipeline, and writes the track, the spoken cues, the spoken title and the poster
into `tv/`. Answers are cached per frame, word budget, brief and model under
`$TMPDIR/aloud-films/<id>/out/described.cache.json`, so a rerun after a rate
limit resumes rather than restarts, and a different model is asked afresh.

## Tears of Steel with its cast, and the continuity pass

Tears of Steel's shipped track was written before it had a cast list. To
re-describe it with the names its dialogue uses (Thom, Celia, Barley, the
Captain) and then run the continuity pass over the result, on a Mac with the
films fetched:

```bash
pip install -r requirements.txt kokoro-onnx soundfile
mkdir -p ~/.cache/aloud/kokoro && cd ~/.cache/aloud/kokoro && \
  curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx && \
  curl -LO https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin && cd -
export ALOUD_TTS=kokoro            # the shelf's voice (the default once its model files are in place)
export GEMINI_API_KEY=...          # or ALOUD_LLM_BASE_URL / _API_KEY / _MODEL
export ALOUD_CONTINUITY=1          # the continuity pass, with the same model
python3 -m aloud.films build --only tears-of-steel
python3 -m aloud.evaluate "$TMPDIR/aloud-films/tears-of-steel/tears_of_steel_720p.mov" \
  --stems TOS_DVDSTEREOMIX.aif "TOS_MUSIC+FX_NO_DIALOGUE.aif" \
  --captions "$TMPDIR/aloud-films/tears-of-steel/TOS-en.srt" \
  --track "$TMPDIR/aloud-films/tears-of-steel/out/description.json"
```

The track then records `describer` (the vision model) and `revised_by` (the
continuity model), and every revised cue keeps what the describer first wrote
as `draft`. Re-check the overlap figure with the evaluate line before quoting
it, and update the counts in README.md and docs/SUBMISSION.md.

The pass is off unless `ALOUD_CONTINUITY=1`. It sends the whole cue list, the
caption lines and the cast list to a text model and asks only for
consistency: the same words for the same person or thing, a cast name once
the person can be told, articles, present tense, nothing added. A revision
is kept only if it passes the sentence gate, names no one the cue or the cast
list did not, is at most two words longer, and, re-spoken and re-measured,
still ends inside the cue's gap. Otherwise the original stays. It is tested
with a fake model (`tests/test_continuity.py`); no shipped track has been
through it.

## The voice

`aloud/synth.py` speaks with **Kokoro 82M** (`kokoro-onnx`, Apache 2.0) when
its model files are in place, and otherwise with macOS `say`. Kokoro is a
neural voice that runs on a CPU faster than real time. The shipped cues are Kokoro's `af_heart`. Model files go
in `~/.cache/aloud/kokoro/` (`kokoro-v1.0.onnx`, `voices-v1.0.bin`, from
github.com/thewh1teagle/kokoro-onnx releases). `ALOUD_TTS=say|kokoro` forces
one; `ALOUD_VOICE` picks a Kokoro voice.

Whichever voice speaks, the schedule is built on the measured length of what it
actually said, never an estimate.

## What the brief asks for

From `aloud/caption.py`, in short: present tense; only what is visible; no
interpretation, no emotions named, nothing that can be heard; no character
names unless the title has a cast list, and then only those; people described by what can be seen of them; legible on-screen text
read as "On screen:" and the words; the most important new thing first; one
sentence; about N words, where N comes from the gap. When the describer can
take them it is also shown a second frame a second later in the same shot, so
it can describe the action rather than a still, and the last three things said,
so it says what is new.
