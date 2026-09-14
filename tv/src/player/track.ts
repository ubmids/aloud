/**
 * The description track the app consumes.
 *
 * This is the artefact the backend produces: cues with times, text, and a
 * pointer to the audio already synthesised for each one. The app does not
 * generate anything. It does not see the picture either, because Vega gives a
 * React Native app the W3C media surface and nothing below it, so there are no
 * frames to look at even if it wanted to.
 *
 * That separation is the design, not a limitation worked around. A track is a
 * standard artefact: cacheable, reviewable by a human describer before it goes
 * out, and identical to what professional audio description ships as.
 */

export type Cue = {
  start: number;
  end: number;
  text: string;
  /** Pre-synthesised speech for this cue. */
  audio?: string | null;
  /** The gap in the dialogue this cue was placed inside. */
  gap?: [number, number] | null;
};

export type Track = {
  source: string;
  cues: Cue[];
};

export type Density = 'full' | 'sparse';

/**
 * How much to say. Sparse keeps only the cues with the most room, which are
 * usually the ones describing the biggest changes, and is what a viewer who
 * finds full description tiring actually wants.
 *
 * It is a filter over an existing track rather than a re-generation, so it
 * costs nothing at playback and cannot introduce a cue that was never
 * validated against a gap.
 */
export function atDensity(track: Track, density: Density): Cue[] {
  if (density === 'full') return track.cues;
  const sorted = [...track.cues].sort(
    (a, b) => b.end - b.start - (a.end - a.start),
  );
  const keep = new Set(sorted.slice(0, Math.ceil(sorted.length / 2)));
  return track.cues.filter((c) => keep.has(c));
}

export function totalSpokenSeconds(cues: Cue[]): number {
  return cues.reduce((n, c) => n + (c.end - c.start), 0);
}

/** Parse the JSON the backend writes. Tolerant, because a malformed track
 *  should leave the film playing rather than take the app down: no description
 *  is a worse experience, but a crash is a broken product. */
export function parseTrack(raw: unknown): Track {
  const obj = (raw ?? {}) as Record<string, unknown>;
  const cues = Array.isArray(obj.cues) ? obj.cues : [];
  return {
    source: typeof obj.source === 'string' ? obj.source : '',
    cues: cues
      .map((c) => c as Record<string, unknown>)
      .filter(
        (c) =>
          typeof c.start === 'number' &&
          typeof c.end === 'number' &&
          typeof c.text === 'string' &&
          c.text.trim().length > 0 &&
          (c.end as number) > (c.start as number),
      )
      .map((c) => ({
        start: c.start as number,
        end: c.end as number,
        text: (c.text as string).trim(),
        audio: typeof c.audio === 'string' ? c.audio : null,
        gap: Array.isArray(c.gap) && c.gap.length === 2
          ? ([c.gap[0], c.gap[1]] as [number, number])
          : null,
      }))
      .sort((a, b) => a.start - b.start),
  };
}
