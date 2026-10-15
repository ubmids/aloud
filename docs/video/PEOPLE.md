# The people in the video: who, what to film, and consent

Everything in the video that does not need a person is already rendered
(see [SHOTS.md](SHOTS.md)). Two things need people, and nothing else does:

| segment | who | length in the cut | needed by |
|---|---|---|---|
| A. Subomi, to camera | Subomi | about 15 s in total (two pieces) | Mon 19 Oct |
| B. A blind or low-vision viewer | someone recruited (below) | 20 to 30 s | Wed 21 Oct |

The cut works without B (there is a written fallback), but B is the shot
that moves Impact and Design the most. Start recruiting first, today.

---

## A. Subomi on camera (about 15 seconds of the final cut)

Film on a phone, landscape, 1080p or better, at eye level, in a quiet room
with a window or lamp in front of you, not behind. Use the phone's own
microphone close to you (an arm's length) or a cheap lavalier; no music.
Record each line three or four times and keep the best. Plain voice, no
pitch tone. Say it to one person, not to an audience.

**A1, at 0:20 (5 to 7 s).** Seated, a TV or laptop showing the aloud shelf
behind or beside you if you can (the screenshots in `docs/video/assets/`
work on a laptop screen).

> "I'm Subomi. I built aloud: a Fire TV that tells you what's on screen,
> in the gaps between the dialogue."

**A2, at 2:35 (6 to 8 s).** Same set-up.

> "Look away, close your eyes, or never see the screen at all. aloud
> keeps you in the film. It's on GitHub, and any Vega app can use it."

**Optional A3, hands only (5 s, no face).** Your hand on a remote or a
keyboard, pressing right, right, select, filmed over the shoulder with the
VVD on the laptop screen. Only if the remote is not a prop that pretends to
be something it is not: a keyboard on the VVD is the honest version.

Do not say "live", "real time", or that a blind viewer has tested it unless
segment B was filmed.

---

## B. A blind or low-vision viewer (20 to 30 seconds of the final cut)

### What we are asking for

About 30 minutes of someone's time, in person or on a video call: they
listen to two minutes of Tears of Steel, once without description and once
with aloud, then answer one question and say one unscripted sentence about
it. Their face is optional: hands, voice, or the back of their head is
enough, and an audio-only contribution over a still is fine.

### Who to ask (most likely first)

1. **Your own network.** One message to friends and family: "Do you know
   anyone who is blind or has low vision and would give 30 minutes to try
   something I built? Paid." The quickest yes usually comes this way.
2. **Nigeria Association of the Blind**, Lagos state branch, and the
   **Lagos State Vocational Rehabilitation Centre** for adults with vision
   loss. Ask for someone comfortable with technology.
3. **University disability offices**: the University of Lagos Students
   with Disabilities support unit, or the special education department at
   the Federal College of Education (Special), Oyo. Students are often keen
   and available at short notice.
4. **Remote, worldwide**: r/Blind (read its rules first and message the
   moderators), the AppleVis forum, the Be My Eyes community. A video call
   works: share the two clips in `docs/video/assets/` as audio and record
   the call with consent.

Offer a fee (N20,000 to N30,000, or $20 to $30 remote) and say so in the
first message. It is good practice, and it makes saying yes easier.

### Message to send

> Hello. I'm Subomi, a developer in Lagos. I've built aloud, an app for
> Fire TV that adds spoken description to films, in the pauses between
> the dialogue, for people who are blind or have low vision. I'm entering
> it in an Amazon developer competition and would like one person with
> vision loss to try two minutes of it and tell me honestly what they
> think, on camera or voice only. It takes about 30 minutes, in person in
> Lagos or by video call, and I'll pay N25,000 for your time. Would you,
> or someone you know, be willing?

### What to film (the session)

Two cameras if you have them (a phone on the viewer, the laptop recording
the call or the screen); one is enough.

1. **Set-up (not used in the cut).** Explain what will happen, read the
   consent form aloud, record the verbal "yes", get the signature or
   written reply.
2. **Without** (play `assets/tos-without.mp4`, 1:31 to 2:10 of the film,
   sound only, narration off). Then ask: **"What happened in that scene?"**
   Film the answer.
3. **With aloud** (play `assets/tos-with.mp4`, the same 39 seconds, with
   aloud's descriptions). Ask the same question. Film the answer.
4. **One measurable question**: "What was over the city, and what was the
   man with the rifle doing?" (the track says a flying ship, descending;
   Barley aiming down at the old man). Note whether they answer correctly,
   without and with aloud. This sentence goes
   in the submission text, whatever the answer is.
5. **One open question**: "Would you use this? What's missing?" Keep
   whatever they say, including criticism. A real criticism on camera is
   more credible than praise.

Do not coach the answers, do not ask leading questions ("wasn't that
great?"), and do not cut an answer to change its meaning.

Their name on screen: `design/assets/src/render.sh lower-third "First name"
"Low vision"` makes the lower third in the video's style.

**In the cut:** 4 to 6 s of the "without" answer, 6 to 10 s of the "with"
answer, and their open sentence. Caption their words on screen in large
type, since an automated pre-screen reads captions.

### Consent wording (read aloud and get it signed or written back)

> **Consent to appear in a video: aloud**
>
> I agree to take part in a short test of aloud, an audio description app
> made by Subomi Olagoke, and to be filmed or recorded while I do.
>
> I agree that the recording, my words, and my first name (or no name, if
> I tick here: [ ]) may be used in a demonstration video published
> publicly on YouTube or Vimeo, and in the written description of the
> project, for the Amazon "Build, Ship, Shape" developer hackathon and
> afterwards to show the project.
>
> I understand that:
> - taking part is voluntary, and I can stop at any time during the
>   session without giving a reason;
> - I can ask for my part to be removed before the video is published
>   (before 22 October 2026) by contacting Subomi at solagoke21@gmail.com;
> - my face does not have to be shown: [ ] face may be shown
>   [ ] hands and voice only [ ] voice only;
> - I will be paid ________ for my time, whether or not the recording is
>   used.
>
> Name: ____________________ Signature or "I agree" by message: __________
> Date: ____________ Witness (if signed by mark): ____________________

For someone who cannot read print: read the form aloud on camera before
the session, record their spoken agreement, and send them the text by
email or message so their screen reader can read it; their written "I
agree" reply counts as the signature. Keep the recording and the reply.

### If nobody is found by Wed 21 Oct

Use the fallback in [SCRIPT.md](SCRIPT.md) (0:50): Subomi with a sleep mask
on, listening, and the line "I can see. Most people watching this can. So
here's the same scene with the picture taken away." Claim nothing about
blind viewers; the README already says no blind viewer has tested it.
