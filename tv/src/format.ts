/** Times on screen, in the two shapes this app needs them. */

/** A position in the film. */
export function clock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;
}

/**
 * A length a viewer is being asked to compare against another length.
 *
 * One decimal, because the entire claim lives in tenths. A silence of 1.9
 * seconds holding 1.3 seconds of speech is the product working; rounded to
 * whole seconds it reads as two seconds of speech in two seconds of silence,
 * which is the product failing.
 */
export function secs(seconds: number): string {
  return `${Math.max(0, seconds).toFixed(1)}s`;
}
