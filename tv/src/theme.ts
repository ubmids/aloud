/**
 * Colour and type in one place, because in this app both are accessibility
 * decisions rather than taste.
 *
 * Two rules govern everything here.
 *
 * The first is contrast. Any tone that carries words clears 4.5:1 against the
 * surface it sits on. That retired the old `#6f5f54`, which measures 3.2:1 on
 * the ground and was being used for four separate pieces of real information.
 * Dimmer tones survive only as hairlines and fills, where nothing is read. An
 * app about not being able to see the picture cannot ship labels that need
 * good eyes.
 *
 * The second is that nothing is said with hue alone. The timeline's three
 * states are separated by lightness as much as colour, so they stay distinct
 * in greyscale and to a colour blind viewer, and each is named in the legend
 * as well as drawn.
 *
 * The scale starts at 17px and the eyebrows are tracked out rather than shrunk.
 * A television is read from three metres, where the 12px captions of the first
 * version were decoration pretending to be labels.
 */
import {Dimensions} from 'react-native';

/**
 * Everything below is drawn in a 1920 by 1080 grid and scaled to whatever
 * surface the app is actually given.
 *
 * A television app cannot check its own layout by eye during development and
 * the interesting failure is silent: on a 720p surface a design with fixed
 * heights does not look cramped, it pushes the film off the bottom of the
 * screen and the four blocks above it look perfectly correct. Scaling from the
 * measured window is the cheap way to never find that out from a judge.
 *
 * It only ever scales down. A larger surface reports larger logical pixels
 * already, and multiplying a second time would give a 4K television enormous
 * type for no reason.
 */
export const u = (n: number): number =>
  Math.round(n * Math.min(1, Dimensions.get('window').height / 1080));

export const palette = {
  /** The room. Warm black, so the picture is the brightest thing present. */
  ground: '#0b0908',
  /** A raised surface: the voice panel, a control. */
  panel: '#15100e',
  /** A cut into the surface: a silence, the inside of the film frame. */
  recess: '#070505',
  edge: '#2a211c',

  ink: '#f7f1ea',
  /** 9:1 on panel. Secondary words. */
  inkSoft: '#c2ae9d',
  /** 6.4:1 on ground. The dimmest tone allowed to carry a word. */
  inkMuted: '#a4907f',

  /** Someone in the film is talking. Mid lightness, the default state. */
  dialogue: '#4a3b33',
  /** Aloud is talking. The only saturated thing on the screen. */
  voice: '#ff7a45',
  voiceDim: '#8a3f22',
  voiceWash: '#2b1811',
};

export const size = {
  wordmark: u(34),
  strap: u(21),
  /** Tracked-out uppercase. Never smaller than this, at any distance. */
  eyebrow: u(17),
  body: u(21),
  lead: u(26),
  /** The description itself, which is the product. */
  cue: u(38),
};
