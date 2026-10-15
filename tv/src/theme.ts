/**
 * Colour, type and space in one place, because in this app all three are
 * accessibility decisions rather than taste. The binding spec is
 * `design/DESIGN.md` (direction: Signal); every ratio below comes from
 * `design/contrast.py`.
 *
 * Signal is the colour of access on television already: near-black, ink, and
 * caption yellow. Yellow means one thing, aloud is speaking. Focus is never
 * yellow; it is an inversion to ink, a frame and a lift, so it survives a
 * greyscale screenshot and a colour blind viewer.
 *
 * Nothing is smaller than 24 px at 1080p and nothing is set in tracked-out
 * capitals: low-vision readers read word shapes, and capitals erase them.
 */
import {Dimensions} from 'react-native';

/**
 * Everything below is drawn in a 1920 by 1080 grid and scaled to whatever
 * surface the app is actually given.
 *
 * A television app cannot check its own layout by eye during development and
 * the interesting failure is silent: on a 720p surface a design with fixed
 * heights does not look cramped, it pushes the film off the bottom of the
 * screen and the blocks above it look perfectly correct. Scaling from the
 * measured window is the cheap way to never find that out from a judge.
 *
 * It only ever scales down. A larger surface reports larger logical pixels
 * already, and multiplying a second time would give a 4K television enormous
 * type for no reason.
 */
export const u = (n: number): number =>
  Math.round(n * Math.min(1, Dimensions.get('window').height / 1080));

export const palette = {
  /** The room. */
  ground: '#0B0B0A',
  /** A surface: an unfocused tile or setting. Separated by tone, not outline. */
  raised: '#171716',
  /** A cut into the surface: a silence, the space behind the film. */
  recess: '#000000',
  /** Hairlines only. Never carries a word. */
  line: '#3A3A37',

  /** 17.7:1 on ground. Words, and the fill of whatever has focus. */
  ink: '#F4F3EE',
  /** 11.6:1 on ground. Secondary words. */
  inkSoft: '#C8C7C0',
  /** 7.7:1 on ground. The dimmest tone allowed to carry a word. */
  inkMuted: '#A3A29B',

  /** Aloud is speaking. Nothing else is this colour. 13.6:1 on ground. */
  voice: '#FFD23F',
  /** Text on a voice fill. */
  onVoice: '#0B0B0A',
  /** Someone in the film is talking. 3.3:1 against a silence, 4.2:1 under the voice. */
  dialogue: '#63635F',
  /** Something went wrong. 8.6:1 on ground. */
  alert: '#FF8A7A',
  /** Behind a full-screen caption. */
  scrim: 'rgba(0,0,0,0.85)',
};

/**
 * Atkinson Hyperlegible Next and Mono, drawn by the Braille Institute for
 * low-vision readers (SIL OFL, `assets/fonts/`). One family per weight, named
 * after its file, because that is how Vega finds a bundled font. The weight is
 * given as well, so a renderer that cannot find the file still draws the
 * hierarchy in its own sans.
 */
export const font = {
  regular: {fontFamily: 'AtkinsonHyperlegibleNext-Regular', fontWeight: '400'},
  semibold: {fontFamily: 'AtkinsonHyperlegibleNext-SemiBold', fontWeight: '600'},
  heavy: {fontFamily: 'AtkinsonHyperlegibleNext-ExtraBold', fontWeight: '800'},
  mono: {fontFamily: 'AtkinsonHyperlegibleMono-Regular', fontWeight: '400'},
  monoSemibold: {fontFamily: 'AtkinsonHyperlegibleMono-SemiBold', fontWeight: '600'},
} as const;

/** The type scale, in px at 1080p. Nothing smaller than `label`. */
export const size = {
  /** The focused film's title. */
  display: u(80),
  /** Player title, the wordmark on the shelf. */
  title: u(52),
  /** The description itself, which is the product. */
  cue: u(46),
  /** Setting values, tile titles, the described line. */
  lead: u(34),
  /** Synopsis, help lines. */
  body: u(28),
  /** Labels, timecodes, counts. The floor. */
  label: u(24),
};

export const line = {
  display: u(84),
  title: u(60),
  cue: u(60),
  lead: u(44),
  body: u(40),
  label: u(32),
};

/** The Fire TV overscan margin: 5% of 1920 by 1080. */
export const safe = {x: u(96), y: u(54)};

/** Focus: a frame, an inversion and a lift, all at once. */
export const focus = {frame: u(6), lift: 1.04, ms: 120};
