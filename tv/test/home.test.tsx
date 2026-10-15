import React from 'react';
import {AccessibilityInfo} from 'react-native';
import {act, fireEvent, render} from '@testing-library/react-native';

import type {Film} from '../src/film';
import {Home} from '../src/screens/Home';
import {DEFAULTS} from '../src/settings';

function makeFilm(id: string, title: string): Film {
  return {
    id, title, year: 2012, minutes: 12, genre: 'Science fiction', synopsis: 's',
    credit: '(CC) Blender Foundation', licence: 'CC BY 3.0, Blender Foundation',
    poster: {uri: `${id}.jpg`},
    track: {source: '', cues: [{start: 1, end: 2, text: 'A ship.'}]},
    describer: 'qwen3-vl-4b (local, llama.cpp on CPU)', voice: 'Kokoro 82M (af_heart)',
    spoken: `${title}. Science fiction, 2012, 12 minutes. 1 descriptions.`,
  };
}

const films = [makeFilm('a', 'Tears of Steel'), makeFilm('b', 'Sintel')];

function fakeSpeaker() {
  return {play: jest.fn(() => true), stop: jest.fn(), setVolume: jest.fn()} as any;
}

async function screen(opts: {reader?: boolean} = {}) {
  jest.spyOn(AccessibilityInfo, 'isScreenReaderEnabled')
    .mockResolvedValue(!!opts.reader);
  const speaker = fakeSpeaker();
  const onPlay = jest.fn();
  const onSettings = jest.fn();
  const r = render(
    <Home films={films} settings={DEFAULTS} onSettings={onSettings}
          onPlay={onPlay} speaker={speaker} />,
  );
  await act(async () => {});
  return {...r, speaker, onPlay, onSettings};
}

test('moving onto a title reads it aloud, cutting off the last one', async () => {
  const {getByTestId, speaker} = await screen();
  fireEvent(getByTestId('tile-b'), 'focus');
  expect(speaker.stop).toHaveBeenCalled();
  expect(speaker.play).toHaveBeenLastCalledWith('/pkg/assets/films/b/announce.m4a');
});

test('the panel follows focus and names who described the film, in words', async () => {
  const {getByTestId, getAllByText, getByText, queryByText} = await screen();
  fireEvent(getByTestId('tile-b'), 'focus');
  expect(getAllByText('Sintel').length).toBeGreaterThan(0);
  expect(getByText('Described ahead of time by Qwen3-VL, an open model. Read by Kokoro.'))
    .toBeTruthy();
  // No model IDs or voice codes in front of a viewer.
  expect(queryByText(/qwen3-vl-4b|af_heart|llama\.cpp/)).toBeNull();
});

test('with VoiceView on, the app stays quiet and lets it read the label', async () => {
  const {getByTestId, speaker} = await screen({reader: true});
  fireEvent(getByTestId('tile-b'), 'focus');
  expect(speaker.play).not.toHaveBeenCalled();
  expect(getByTestId('tile-b').props.accessibilityLabel)
    .toBe('Sintel. Science fiction, 2012, 12 minutes. 1 descriptions.');
});

test('select plays the title; the settings change what the player will do', async () => {
  const {getByTestId, onPlay, onSettings} = await screen();
  fireEvent.press(getByTestId('tile-a'));
  expect(onPlay).toHaveBeenCalledWith(films[0]);
  fireEvent.press(getByTestId('home-level'));
  expect(onSettings).toHaveBeenLastCalledWith({...DEFAULTS, level: 'loud'});
  fireEvent.press(getByTestId('home-narration'));
  expect(onSettings).toHaveBeenLastCalledWith({...DEFAULTS, narration: false});
  fireEvent.press(getByTestId('home-density'));
  expect(onSettings).toHaveBeenLastCalledWith({...DEFAULTS, density: 'sparse'});
});
