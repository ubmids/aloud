import React, {useState} from 'react';
import {AccessibilityInfo} from 'react-native';
import {act, fireEvent, render} from '@testing-library/react-native';

import type {Film} from '../src/film';
import UI from '../src/data/ui.json';
import {Home} from '../src/screens/Home';
import {Player} from '../src/screens/Player';
import {DEFAULTS, type Settings} from '../src/settings';

/**
 * Every focus change and every value change is spoken, in the app's own
 * voice, for a viewer who cannot see which setting the remote is on.
 *
 * Moving down from the shelf to "Voice level" used to say nothing at all.
 */

jest.mock('@amazon-devices/react-native-kepler', () => {
  const actual = jest.requireActual('@amazon-devices/react-native-kepler');
  return new Proxy(actual, {
    get(target, key) {
      if (key === 'useTVEventHandler') return () => {};
      if (key === 'useComponentInstance') return () => ({});
      return target[key];
    },
  });
});
jest.mock('@amazon-devices/react-native-w3cmedia', () => ({Video: () => null}));

const clip = (key: string) => `/pkg/assets/ui/${key}.m4a`;

function makeFilm(id: string, title: string): Film {
  return {
    id, title, year: 2012, minutes: 12, genre: 'Science fiction', synopsis: 's',
    credit: 'c', licence: 'l', poster: {uri: `${id}.jpg`},
    track: {source: '', cues: [{start: 1, end: 2, text: 'A ship.', gap: [0.5, 3]}]},
    describer: 'd', voice: 'v', spoken: `${title}.`,
  };
}
const films = [makeFilm('a', 'Tears of Steel'), makeFilm('b', 'Sintel')];

function fakeSpeaker() {
  return {play: jest.fn(() => true), stop: jest.fn(), setVolume: jest.fn(),
          speak: jest.fn()} as any;
}

/** The screen with real settings state, the way App holds it. */
function Stateful({screen, start, speaker}: {
  screen: 'home' | 'player'; start: Settings; speaker: any;
}) {
  const [settings, setSettings] = useState(start);
  return screen === 'home'
    ? <Home films={films} settings={settings} onSettings={setSettings}
            onPlay={() => {}} speaker={speaker} />
    : <Player film={films[0]} settings={settings} onSettings={setSettings}
              speaker={speaker} />;
}

async function open(screen: 'home' | 'player',
                    opts: {reader?: boolean; settings?: Settings} = {}) {
  jest.spyOn(AccessibilityInfo, 'isScreenReaderEnabled')
    .mockResolvedValue(!!opts.reader);
  const speaker = fakeSpeaker();
  const r = render(<Stateful screen={screen} start={opts.settings ?? DEFAULTS}
                             speaker={speaker} />);
  await act(async () => {});
  speaker.play.mockClear();
  return {...r, speaker};
}

test('every clip the app can play has words', () => {
  for (const [key, words] of Object.entries(UI)) {
    expect(typeof words).toBe('string');
    expect((words as string).length).toBeGreaterThan(5);
    expect(key).toMatch(/^[a-z-]+$/);
  }
});

describe('on the shelf', () => {
  test.each([
    ['home-narration', 'narration-on', 'narration-off'],
    ['home-level', 'level-normal', 'level-loud'],
    ['home-speak-menus', 'menus-on', 'menus-off'],
  ])('%s says its name and value on focus, and its new value on select',
     async (id, onFocus, afterPress) => {
    const {getByTestId, speaker} = await open('home');
    fireEvent(getByTestId(id), 'focus');
    expect(speaker.stop).toHaveBeenCalled();
    expect(speaker.play).toHaveBeenLastCalledWith(clip(onFocus));
    fireEvent.press(getByTestId(id));
    expect(speaker.play).toHaveBeenLastCalledWith(clip(afterPress));
  });

  test('voice level goes all the way round, each step spoken', async () => {
    const {getByTestId, speaker} = await open('home');
    fireEvent(getByTestId('home-level'), 'focus');
    for (const next of ['level-loud', 'level-quiet', 'level-normal']) {
      fireEvent.press(getByTestId('home-level'));
      expect(speaker.play).toHaveBeenLastCalledWith(clip(next));
    }
  });

  test('with VoiceView on, the settings are left to VoiceView', async () => {
    const {getByTestId, speaker} = await open('home', {reader: true});
    fireEvent(getByTestId('home-level'), 'focus');
    fireEvent.press(getByTestId('home-level'));
    expect(speaker.play).not.toHaveBeenCalled();
  });

  test('with the menu voice off, settings are quiet, except to confirm turning it on',
       async () => {
    const {getByTestId, speaker} = await open('home', {
      settings: {...DEFAULTS, speakMenus: false}});
    fireEvent(getByTestId('home-level'), 'focus');
    fireEvent.press(getByTestId('home-level'));
    expect(speaker.play).not.toHaveBeenCalled();
    fireEvent(getByTestId('home-speak-menus'), 'focus');
    fireEvent.press(getByTestId('home-speak-menus'));
    expect(speaker.play).toHaveBeenLastCalledWith(clip('menus-on'));
  });
});

describe('in the player', () => {
  test.each([
    ['toggle-enabled', 'narration-on', 'narration-off'],
    ['toggle-level', 'level-normal', 'level-loud'],
    ['toggle-density', 'density-full', 'density-sparse'],
    ['toggle-picture', 'picture-panel', 'picture-full'],
  ])('%s says its name and value on focus, and its new value on select',
     async (id, onFocus, afterPress) => {
    const {getByTestId, speaker} = await open('player');
    fireEvent(getByTestId(id), 'focus');
    expect(speaker.play).toHaveBeenLastCalledWith(clip(onFocus));
    fireEvent.press(getByTestId(id));
    expect(speaker.play).toHaveBeenLastCalledWith(clip(afterPress));
  });

  test('a value the player changes by itself is not spoken over the film', async () => {
    jest.spyOn(AccessibilityInfo, 'isScreenReaderEnabled').mockResolvedValue(false);
    const speaker = fakeSpeaker();
    const at = (level: Settings['level']) => (
      <Player film={films[0]} settings={{...DEFAULTS, level}}
              onSettings={() => {}} speaker={speaker} />);
    const {getByTestId, rerender} = render(at('normal'));
    await act(async () => {});
    fireEvent(getByTestId('toggle-level'), 'focus');
    speaker.play.mockClear();
    // Settings changed from elsewhere while focused: nobody pressed select
    // here, so nothing is announced.
    rerender(at('quiet'));
    expect(speaker.play).not.toHaveBeenCalled();
  });
});
