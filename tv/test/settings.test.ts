import {DEFAULTS, filmVolume, LEVELS, nextLevel, VOICE_LEVELS} from '../src/settings';

describe('voice level', () => {
  test('select cycles quiet, normal, loud and back', () => {
    expect(nextLevel('quiet')).toBe('normal');
    expect(nextLevel('normal')).toBe('loud');
    expect(nextLevel('loud')).toBe('quiet');
  });

  test('a louder level is a louder voice over a lower film', () => {
    for (let i = 1; i < VOICE_LEVELS.length; i++) {
      const lo = LEVELS[VOICE_LEVELS[i - 1]];
      const hi = LEVELS[VOICE_LEVELS[i]];
      expect(hi.voice).toBeGreaterThan(lo.voice);
      expect(hi.film).toBeLessThan(lo.film);
    }
  });

  test('the film only dips while a description is being spoken', () => {
    // The scheduler only ever speaks inside a gap in the dialogue, so this is
    // what guarantees no line of dialogue is turned down.
    expect(filmVolume('loud', false, true)).toBe(1);
    expect(filmVolume('loud', true, true)).toBe(LEVELS.loud.film);
    expect(filmVolume('loud', true, false)).toBe(1);
  });

  test('narration is on by default, so the app works for the person it is for', () => {
    expect(DEFAULTS.narration).toBe(true);
    expect(DEFAULTS.speakMenus).toBe(true);
  });
});
