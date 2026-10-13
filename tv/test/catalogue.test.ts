import * as fs from 'fs';
import * as path from 'path';

import {announcement, FILMS} from '../src/catalogue';
import {cueWindow} from '../src/player/schedule.js';

const ASSETS = path.join(__dirname, '..', 'assets', 'films');

// A description must never end on one of these: the listener is left waiting
// for a noun that never arrives. Same list as aloud/budget.py, less "her",
// which ends a whole sentence as an object ("...rock formations behind her.").
const DANGLING = new Set([
  'a', 'an', 'the', 'and', 'or', 'but', 'as', 'of', 'in', 'on', 'at', 'to',
  'for', 'with', 'from', 'into', 'over', 'under', 'by', 'his', 'its',
  'their', 'this', 'that', 'these', 'those', 'is', 'was', 'are', 'were',
  'then', 'while', 'when', 'who', 'which', 'very', 'more', 'two', 'three',
]);

describe.each(FILMS.map((f) => [f.id, f] as const))('%s', (_id, film) => {
  test('carries real descriptions, written by a named model', () => {
    expect(film.track.cues.length).toBeGreaterThan(3);
    expect(film.describer).not.toBe('');
    expect(film.describer).not.toMatch(/stub/i);
    for (const c of film.track.cues) {
      expect(c.text).not.toMatch(/^The scene changes/);
      expect(c.text).toMatch(/[.!?"]$/);
      const last = c.text.replace(/[^A-Za-z' ]/g, '').trim().split(/\s+/).pop()!;
      expect(DANGLING.has(last.toLowerCase())).toBe(false);
    }
  });

  test('every cue sits inside its gap and after the one before it', () => {
    let end = 0;
    for (const c of film.track.cues) {
      const w = cueWindow(c);
      expect(c.start).toBeGreaterThanOrEqual(w.opens - 0.01);
      expect(c.end).toBeLessThanOrEqual(w.end + 0.01);
      expect(c.start).toBeGreaterThanOrEqual(end - 0.01);
      end = c.end;
    }
  });

  test('every cue it names is bundled, and so is its spoken title', () => {
    for (const c of film.track.cues) {
      expect(c.audio).toBeTruthy();
      expect(fs.existsSync(path.join(ASSETS, film.id, 'cues', c.audio!))).toBe(true);
    }
    expect(fs.existsSync(path.join(ASSETS, film.id, 'announce.m4a'))).toBe(true);
  });

  test('the shelf says what the clip says', () => {
    expect(announcement(film)).toContain(film.title);
    expect(announcement(film)).toContain(`${film.track.cues.length} descriptions`);
  });

  test('credits the film as its licence asks', () => {
    expect(film.credit).toMatch(/Blender Foundation/);
    expect(film.licence).toMatch(/CC BY 3\.0/);
  });
});
