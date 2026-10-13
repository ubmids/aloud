import type {ImageSourcePropType} from 'react-native';

import {totalSpokenSeconds, type Track} from './player/track';

/** A title on the shelf. Built from the backend's track file in catalogue.ts. */
export type Film = {
  id: string;
  title: string;
  year: number;
  /** Running time in whole minutes, for the shelf. */
  minutes: number;
  genre: string;
  synopsis: string;
  credit: string;
  licence: string;
  poster: ImageSourcePropType;
  track: Track;
  /** Who wrote and spoke the track, shown so nobody mistakes it for a human
   *  describer's work. */
  describer: string;
  voice: string;
  /** The words of the spoken shelf clip, written by the backend beside it. */
  spoken: string;
};

/** The line under a title that says how much of it is described. */
export function describedSummary(f: Film): string {
  const n = f.track.cues.length;
  const spoken = Math.round(totalSpokenSeconds(f.track.cues) / 60 * 10) / 10;
  return `${n} descriptions, ${spoken} minutes of narration`;
}

/**
 * What the shelf says out loud when a title takes focus.
 *
 * Short on purpose. A viewer moving along the row with the remote hears this
 * once per press, and a sentence that is still going when they press again is
 * one they learn to talk over.
 */
export function announcement(f: Film): string {
  // The backend wrote the clip from these words; using them here means the
  // screen reader and the app's own voice say the same thing.
  if (f.spoken) return f.spoken;
  return `${f.title}. ${f.genre}, ${f.year}, ${f.minutes} ` +
    `minute${f.minutes === 1 ? '' : 's'}. ${f.track.cues.length} descriptions.`;
}
