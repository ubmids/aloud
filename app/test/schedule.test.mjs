import { DescriptionScheduler } from "../src/schedule.js";

let pass = 0, fail = 0;
function t(name, fn) {
  try { fn(); console.log("PASS " + name); pass++; }
  catch (e) { console.log("FAIL " + name + "\n      " + e.message); fail++; }
}
function eq(a, b, m) {
  const A = JSON.stringify(a), B = JSON.stringify(b);
  if (A !== B) throw new Error((m || "") + ` expected ${B}, got ${A}`);
}

// Two gaps, each with a description that fills most of it.
const CUES = [
  { id: "a", start: 2.0, end: 5.0, text: "A man crosses the street.", duration: 2.0 },
  { id: "b", start: 9.0, end: 12.0, text: "Snow fills the courtyard.", duration: 2.4 },
];

function make(opts = {}) {
  const spoken = [], stops = [];
  const s = new DescriptionScheduler(CUES, {
    onSpeak: c => spoken.push(c.id), onStop: () => stops.push(1), ...opts,
  });
  return { s, spoken, stops };
}

// timeupdate fires about four times a second, so that is how it is driven.
function play(s, from, to, step = 0.25, playing = true) {
  for (let t = from; t <= to + 1e-9; t += step) s.update(+t.toFixed(3), playing);
}

t("a cue fires once, inside its window", () => {
  const { s, spoken } = make();
  play(s, 0, 14);
  eq(spoken, ["a", "b"]);
});

t("nothing fires before its window opens", () => {
  const { s, spoken } = make();
  play(s, 0, 1.75);
  eq(spoken, []);
});

t("a cue is never started twice", () => {
  const { s, spoken } = make();
  play(s, 0, 6);
  play(s, 6, 6.5, 0.05);
  eq(spoken, ["a"]);
});

t("a cue is dropped when too little of its window is left", () => {
  // Joining at 3.5 leaves 1.5s of a window for 2.0s of speech.
  const { s, spoken } = make();
  play(s, 3.5, 6);
  eq(spoken, [], "it started a description that could not finish in the gap:");
});

t("a cue whose window has entirely passed is discarded", () => {
  const { s, spoken } = make();
  play(s, 5.5, 8);
  eq(spoken, []);
});

t("nothing fires while paused", () => {
  const { s, spoken } = make();
  play(s, 0, 4, 0.25, false);
  eq(spoken, []);
});

t("speaking is stopped when the viewer pauses", () => {
  const { s, spoken, stops } = make();
  play(s, 0, 2.5);
  eq(spoken, ["a"]);
  s.update(2.6, false);
  eq(stops, [1]);
});

t("two cues never overlap each other", () => {
  const tight = [
    { id: "x", start: 2.0, end: 8.0, text: "one", duration: 3.0 },
    { id: "y", start: 3.0, end: 8.0, text: "two", duration: 2.0 },
  ];
  const spoken = [];
  const s = new DescriptionScheduler(tight, { onSpeak: c => spoken.push(c.id) });
  play(s, 0, 4.5);
  eq(spoken, ["x"], "it began a second description over the first:");
});

t("seeking backwards re-arms a cue so a rewatch is described", () => {
  const { s, spoken } = make();
  play(s, 0, 6);
  eq(spoken, ["a"]);
  s.update(1.0);            // scrub back before the cue
  play(s, 1.0, 5.0);
  eq(spoken, ["a", "a"]);
});

t("seeking forwards past a cue discards it", () => {
  const { s, spoken } = make();
  play(s, 0, 1.5);
  s.update(8.0);            // skip over cue a entirely
  play(s, 8.0, 12);
  eq(spoken, ["b"], "it described a moment the viewer had already skipped:");
});

t("at double speed a window that is now too short is skipped", () => {
  const { s, spoken } = make();
  s.setRate(2);
  // 3.5s leaves 1.5s of window, which at 2x passes in 0.75s of real time.
  play(s, 3.5, 6);
  eq(spoken, []);
});

t("an empty track is harmless", () => {
  const s = new DescriptionScheduler([], {});
  play(s, 0, 10);
  eq(s.speaking, null);
});

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
