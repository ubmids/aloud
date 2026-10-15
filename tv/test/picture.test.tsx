import React, {useState} from 'react';
import {act, fireEvent, render} from '@testing-library/react-native';

import type {Film} from '../src/film';
import {CHROME_MS, Player} from '../src/screens/Player';
import {DEFAULTS, type Settings} from '../src/settings';

/**
 * "Picture: Full screen" makes the player a television player: the film fills
 * the screen, the description being spoken is a caption over it, and the
 * controls fade until a key is pressed. The panel layout is still the default,
 * because it is what shows a sighted viewer what description is.
 */

let mockRemote: ((e: {eventType: string; eventKeyAction?: number}) => void) | null = null;
jest.mock('@amazon-devices/react-native-kepler', () => {
  const actual = jest.requireActual('@amazon-devices/react-native-kepler');
  return new Proxy(actual, {
    get(target, key) {
      if (key === 'useTVEventHandler') return (fn: any) => { mockRemote = fn; };
      if (key === 'useComponentInstance') return () => ({});
      return target[key];
    },
  });
});
const mockFilm = {
  currentTime: 0, paused: false, duration: 734, volume: 1,
  play: jest.fn(function (this: any) { this.paused = false; }),
  pause: jest.fn(function (this: any) { this.paused = true; }),
};
// Every Video the player mounts, with the size and source it was given.
const mockMounts: {width: number; height: number; props: any}[] = [];
jest.mock('@amazon-devices/react-native-w3cmedia', () => {
  const R = require('react');
  return {
    Video: R.forwardRef((props: any, ref: any) => {
      const me = R.useRef(null);
      if (me.current === null) {
        me.current = {width: props.width, height: props.height, props};
        mockMounts.push(me.current);
      }
      me.current.props = props;
      R.useEffect(() => { if (typeof ref === 'function') ref(mockFilm); }, [ref]);
      return null;
    }),
  };
});

const title: Film = {
  id: 'tears-of-steel', title: 'Tears of Steel', year: 2012, minutes: 12,
  genre: 'Science fiction', synopsis: 's', credit: 'c', licence: 'l',
  poster: {uri: 'p.jpg'}, describer: 'd', voice: 'v', spoken: '',
  track: {source: '', cues: [
    {start: 11.5, end: 14.0, text: 'Rocket engines ignite.', audio: 'cue-001.m4a',
     gap: [10.0, 16.0]},
  ]},
};

function Stateful({start}: {start: Settings}) {
  const [settings, setSettings] = useState(start);
  const speaker = {speak: jest.fn(), stop: jest.fn(), setVolume: jest.fn(),
                   play: jest.fn(() => true)} as any;
  return <Player film={title} settings={settings} onSettings={setSettings}
                 speaker={speaker} />;
}

function open(start: Settings = DEFAULTS) {
  const r = render(<Stateful start={start} />);
  fireEvent(r.getByTestId('stage'), 'layout',
            {nativeEvent: {layout: {width: 1920, height: 1080}}});
  return r;
}

// Nested style arrays, merged the way the renderer merges them.
const merged = (style: any): any => Array.isArray(style)
  ? Object.assign({}, ...style.map(merged)) : (style ?? {});
const opacity = (el: any) => merged(el.props.style).opacity ?? 1;

beforeEach(() => {
  mockMounts.length = 0;
  jest.useFakeTimers();
  mockFilm.currentTime = 0;
  mockFilm.paused = false;
});
afterEach(() => jest.useRealTimers());

test('the default is the panel: film, voice panel, schedule', () => {
  const {getByTestId, queryByTestId, getByText} = open();
  expect(getByTestId('cue-area')).toBeTruthy();
  expect(getByTestId('timeline')).toBeTruthy();
  expect(getByText(/spoken so far, each inside a measured gap/)).toBeTruthy();
  expect(queryByTestId('caption')).toBeNull();
  expect(getByText('With the voice panel')).toBeTruthy();
});

test('full screen hides the panel and the schedule and fills the screen', () => {
  const {getByTestId, queryByTestId, queryByText, getByText} = open();
  fireEvent.press(getByTestId('toggle-picture'));
  expect(getByText('Full screen')).toBeTruthy();
  expect(queryByTestId('cue-area')).toBeNull();
  expect(queryByTestId('timeline')).toBeNull();
  expect(queryByText(/spoken so far/)).toBeNull();
  const stage = merged(getByTestId('stage').props.style);
  expect(stage).toMatchObject({position: 'absolute', top: 0, left: 0, right: 0, bottom: 0});
});

test('in full screen the description being said is a caption over the film', () => {
  const {getByTestId, queryByTestId} = open({...DEFAULTS, picture: 'full'});
  expect(queryByTestId('caption')).toBeNull();
  mockFilm.currentTime = 30;
  act(() => mockRemote?.({eventType: 'menu', eventKeyAction: 1}));
  expect(getByTestId('caption')).toBeTruthy();
  expect(getByTestId('caption').props.children.props.children).toBe('Rocket engines ignite.');
});

test('the controls fade after a few seconds and any key brings them back', () => {
  const {getByTestId} = open({...DEFAULTS, picture: 'full'});
  expect(opacity(getByTestId('controls'))).toBe(1);
  act(() => jest.advanceTimersByTime(CHROME_MS + 10));
  expect(opacity(getByTestId('controls'))).toBe(0);
  act(() => mockRemote?.({eventType: 'down', eventKeyAction: 1}));
  expect(opacity(getByTestId('controls'))).toBe(1);
});

test('back to the panel, everything returns and stays', () => {
  const {getByTestId} = open({...DEFAULTS, picture: 'full'});
  fireEvent.press(getByTestId('toggle-picture'));
  act(() => jest.advanceTimersByTime(CHROME_MS * 3));
  expect(getByTestId('cue-area')).toBeTruthy();
  expect(getByTestId('timeline')).toBeTruthy();
  expect(opacity(getByTestId('controls'))).toBe(1);
});

test('a new picture size is a new surface, and the film carries on where it was', () => {
  // Seen on the Vega Virtual Device: Video takes its size once, so full
  // screen left the film at its panel size in the middle of a black screen.
  const {getByTestId} = open();
  fireEvent(getByTestId('stage'), 'layout',
            {nativeEvent: {layout: {width: 1250, height: 700}}});
  const panel = mockMounts.at(-1)!;
  expect(panel).toMatchObject({width: 1250, height: 700});
  act(() => panel.props.onComponentDidMount());
  act(() => jest.advanceTimersByTime(300));
  expect(mockMounts.at(-1)!.props.src).toBe('/pkg/assets/films/tears-of-steel/film.mp4');
  mockFilm.currentTime = 101.5;
  act(() => mockMounts.at(-1)!.props.onTimeUpdate());

  fireEvent.press(getByTestId('toggle-picture'));
  fireEvent(getByTestId('stage'), 'layout',
            {nativeEvent: {layout: {width: 1920, height: 1080}}});
  const full = mockMounts.at(-1)!;
  expect(full).not.toBe(panel);
  expect(full).toMatchObject({width: 1920, height: 1080});
  // Not handed the film before its surface is ready.
  expect(full.props.src).toBeUndefined();
  act(() => full.props.onComponentDidMount());
  act(() => jest.advanceTimersByTime(300));
  expect(full.props.src).toBe('/pkg/assets/films/tears-of-steel/film.mp4');
  mockFilm.currentTime = 0;
  act(() => full.props.onLoadedMetadata());
  expect(mockFilm.currentTime).toBe(101.5);
});
