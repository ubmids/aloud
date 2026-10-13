import type {Film} from './film';
import {parseTrack} from './player/track';
import tearsOfSteel from './data/films/tears-of-steel.json';
import sintel from './data/films/sintel.json';
import sintelTrailer from './data/films/sintel-trailer.json';

/**
 * What is on the shelf.
 *
 * Every title here ships with a description track written before anyone
 * pressed play: the backend found the gaps in its dialogue, an open vision
 * model described each new shot, and a voice was measured into each gap. The
 * app never generates anything at playback. That is the design, and the copy
 * says so: a precomputed track can be reviewed by a person before it airs,
 * and it costs nothing on the device.
 *
 * All three are open films from the Blender Foundation under CC BY 3.0, the
 * only licence that lets a hackathon entry show a real film end to end. The
 * credits travel with each title and are shown on its details panel, as the
 * licence asks.
 */
type Raw = {describer?: string; voice?: string; announcement?: string};

function film(meta: Omit<Film, 'track' | 'describer' | 'voice' | 'spoken'>, raw: unknown): Film {
  const r = (raw ?? {}) as Raw;
  return {
    ...meta,
    track: parseTrack(raw),
    describer: typeof r.describer === 'string' ? r.describer : '',
    voice: typeof r.voice === 'string' ? r.voice : '',
    spoken: typeof r.announcement === 'string' ? r.announcement : '',
  };
}

const BLENDER = 'CC BY 3.0, Blender Foundation';

export const FILMS: Film[] = [
  film({
    id: 'tears-of-steel',
    title: 'Tears of Steel',
    year: 2012,
    minutes: 12,
    genre: 'Science fiction',
    synopsis:
      'In a future Amsterdam overrun by robots, a band of scientists and ' +
      'soldiers restage one moment from the past, a break-up on a bridge, ' +
      'to save the world.',
    credit: '(CC) Blender Foundation | mango.blender.org',
    licence: BLENDER,
    poster: require('./assets/posters/tears-of-steel.jpg'),
  }, tearsOfSteel),
  film({
    id: 'sintel',
    title: 'Sintel',
    year: 2010,
    minutes: 15,
    genre: 'Fantasy',
    synopsis:
      'A young woman crosses a frozen world to find the baby dragon that was ' +
      'taken from her.',
    credit: '(c) copyright Blender Foundation | durian.blender.org',
    licence: BLENDER,
    poster: require('./assets/posters/sintel.jpg'),
  }, sintel),
  film({
    id: 'sintel-trailer',
    title: 'Sintel: the trailer',
    year: 2010,
    minutes: 1,
    genre: 'Trailer',
    synopsis: 'Fifty-two seconds of Sintel, small enough to ship inside the app.',
    credit: '(c) copyright Blender Foundation | durian.blender.org',
    licence: BLENDER,
    poster: require('./assets/posters/sintel-trailer.jpg'),
  }, sintelTrailer),
];

export type {Film} from './film';
export {announcement, describedSummary} from './film';
