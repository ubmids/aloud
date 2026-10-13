import React from 'react';
import {act, fireEvent, render} from '@testing-library/react-native';

import type {Film} from '../src/film';
import {Player} from '../src/screens/Player';
import {DEFAULTS} from '../src/settings';

// The remote, captured: the test presses buttons by calling what the player
// registered, the way the device's input manager would.
let mockRemote: ((e: {eventType: string; eventKeyAction?: number}) => void) | null = null;
jest.mock('@amazon-devices/react-native-kepler', () => {
  const actual = jest.requireActual('@amazon-devices/react-native-kepler');
  // A proxy rather than a spread: the package's exports are lazy getters, and
  // spreading them evaluates every one of them at once.
  return new Proxy(actual, {
    get(target, key) {
      if (key === 'useTVEventHandler') {
        return (fn: any) => {
          mockRemote = fn;
        };
      }
      if (key === 'useComponentInstance') return () => ({});
      return target[key];
    },
  });
});

// A film element with just the parts the player touches.
const mockFilm = {
  currentTime: 0,
  paused: false,
  duration: 734,
  volume: 1,
  play: jest.fn(function (this: any) {
    this.paused = false;
  }),
  pause: jest.fn(function (this: any) {
    this.paused = true;
  }),
};
jest.mock('@amazon-devices/react-native-w3cmedia', () => {
  const R = require('react');
  return {
    Video: R.forwardRef((props: any, ref: any) => {
      R.useEffect(() => {
        if (typeof ref === 'function') ref(mockFilm);
      }, [ref]);
      return null;
    }),
  };
});

const title: Film = {
  id: 'tears-of-steel', title: 'Tears of Steel', year: 2012, minutes: 12,
  genre: 'Science fiction', synopsis: 's', credit: 'c', licence: 'CC BY 3.0',
  poster: {uri: 'p.jpg'}, describer: 'qwen3-vl-4b', voice: 'Kokoro', spoken: '',
  track: {source: '', cues: [
    {start: 11.5, end: 14.0, text: 'Rocket engines ignite.', audio: 'cue-001.m4a',
     gap: [10.0, 16.0]},
    {start: 45.4, end: 47.0, text: 'On screen: 40 YEARS LATER.', audio: 'cue-002.m4a',
     gap: [44.0, 50.0]},
  ]},
};

function speaker() {
  return {speak: jest.fn(), stop: jest.fn(), setVolume: jest.fn(),
          play: jest.fn(() => true)} as any;
}

function open(narration: boolean) {
  const s = speaker();
  const r = render(
    <Player film={title} settings={{...DEFAULTS, narration}}
            onSettings={jest.fn()} speaker={s} />,
  );
  // The player only mounts the film once it knows the size of its stage.
  fireEvent(r.getByTestId('stage'), 'layout',
            {nativeEvent: {layout: {width: 1280, height: 720}}});
  return {...r, speaker: s};
}

function press(eventType: string) {
  act(() => mockRemote?.({eventType, eventKeyAction: 1}));
}

beforeEach(() => {
  jest.useFakeTimers();
  mockFilm.currentTime = 0;
  mockFilm.paused = false;
  mockFilm.play.mockClear();
  mockFilm.pause.mockClear();
  mockRemote = null;
});
afterEach(() => jest.useRealTimers());

test('Menu pauses the film, says the last description again, then carries on', () => {
  const {speaker: s, getByText} = open(true);
  mockFilm.currentTime = 30;
  press('menu');
  expect(mockFilm.pause).toHaveBeenCalled();
  expect(s.speak).toHaveBeenCalledTimes(1);
  expect(s.speak.mock.calls[0][0].text).toBe('Rocket engines ignite.');
  expect(s.speak.mock.calls[0][0].audio).toBe(
    '/pkg/assets/films/tears-of-steel/cues/cue-001.m4a');
  expect(getByText('Rocket engines ignite.')).toBeTruthy();
  expect(mockFilm.play).not.toHaveBeenCalled();
  act(() => jest.advanceTimersByTime(3100));
  expect(mockFilm.play).toHaveBeenCalledTimes(1);
});

test('with narration off, Menu still answers: it is how that viewer asks', () => {
  const {speaker: s} = open(false);
  mockFilm.currentTime = 46;
  press('menu');
  expect(s.speak.mock.calls[0][0].text).toBe('On screen: 40 YEARS LATER.');
});

test('a film the viewer paused stays paused after the answer', () => {
  open(true);
  mockFilm.currentTime = 30;
  mockFilm.paused = true;
  press('menu');
  act(() => jest.advanceTimersByTime(5000));
  expect(mockFilm.play).not.toHaveBeenCalled();
});

test('before anything has been described, Menu says nothing and the film plays on', () => {
  const {speaker: s} = open(true);
  mockFilm.currentTime = 5;
  press('menu');
  expect(s.speak).not.toHaveBeenCalled();
  expect(mockFilm.pause).not.toHaveBeenCalled();
});

test('key-down is ignored, so one press is one answer', () => {
  const {speaker: s} = open(true);
  mockFilm.currentTime = 30;
  act(() => mockRemote?.({eventType: 'menu', eventKeyAction: 0}));
  expect(s.speak).not.toHaveBeenCalled();
});

test('two Menu presses on the lighter setting turn description back up, and say why', () => {
  const {getByTestId, getByText, queryByText} = open(true);
  fireEvent.press(getByTestId('toggle-density'));
  expect(getByText('Only what changed most')).toBeTruthy();
  mockFilm.currentTime = 30;
  press('menu');
  act(() => jest.advanceTimersByTime(3100));
  expect(queryByText('Everything')).toBeNull();
  mockFilm.currentTime = 50;
  press('menu');
  expect(getByText('Everything')).toBeTruthy();
  expect(getByText(/You asked twice in two minutes/)).toBeTruthy();
  // Changing it by hand is the viewer's word, and the explanation goes.
  fireEvent.press(getByTestId('toggle-density'));
  fireEvent.press(getByTestId('toggle-density'));
  expect(queryByText(/You asked twice/)).toBeNull();
});

test('the on-screen tally claims only what was measured: each cue sits in a gap', () => {
  const {getByText, queryByText} = open(true);
  // "none of them over a line" was on screen, and the evaluation measures
  // 0.9 s of overlap on uncaptioned lines. The screen says what is true.
  expect(queryByText(/none of them over a line/)).toBeNull();
  expect(getByText(/spoken so far, each inside a measured gap/)).toBeTruthy();
});
