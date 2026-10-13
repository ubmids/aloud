import type {Density} from './track';

/**
 * Saying more when the viewer keeps asking.
 *
 * "Only what changed most" is the setting for a viewer who finds full
 * description tiring. But every press of Menu is that viewer telling the app it
 * left something out, and two of them close together mean the lighter setting
 * is costing them the film. So the player goes back to saying everything, and
 * says why on the control that changed, rather than waiting for the viewer to
 * find the setting with a remote they cannot see.
 *
 * It only ever moves towards more description, never less: the app turning
 * itself down because nobody asked would be guessing, and a viewer who wants it
 * quieter can say so with one press. And it only reads Menu presses, the one
 * signal that means "I did not catch that". Narration being off is left alone,
 * because that is the sofa where someone else is watching the film as made.
 */
export const ASK_WINDOW_MS = 120_000;
export const ASKS_TO_SAY_MORE = 2;

export const SAID_MORE =
  'You asked twice in two minutes, so everything is said again.';

/** The asks still inside the window, newest last, with `now` added. */
export function remember(asks: number[], now: number): number[] {
  return [...asks.filter((t) => now - t < ASK_WINDOW_MS), now];
}

/** Whether these asks, at this density, mean the viewer needs more said. */
export function shouldSayMore(asks: number[], density: Density): boolean {
  return density === 'sparse' && asks.length >= ASKS_TO_SAY_MORE;
}
