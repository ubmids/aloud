import React from 'react';
import {fireEvent, render} from '@testing-library/react-native';

import {FilmTile} from '../src/components/FilmTile';
import type {Film} from '../src/film';

const film: Film = {
  id: 'x', title: 'Tears of Steel', year: 2012, minutes: 12, genre: 'Science fiction',
  synopsis: '', credit: '', licence: '', poster: {uri: 'poster.jpg'},
  track: {source: '', cues: [{start: 1, end: 2, text: 'A ship.'}]},
  describer: 'm', voice: 'v', spoken: '',
};

test('a focused tile says what select does, and reports its focus', () => {
  const onFocus = jest.fn();
  const onPress = jest.fn();
  const {getByTestId, getByText, queryByText} = render(
    <FilmTile film={film} label="Tears of Steel. 1 descriptions." onFocus={onFocus}
              onPress={onPress} testID="tile" />,
  );
  expect(getByText('1 description')).toBeTruthy();
  fireEvent(getByTestId('tile'), 'focus');
  expect(onFocus).toHaveBeenCalledTimes(1);
  expect(getByText('Select to play')).toBeTruthy();
  expect(queryByText('1 description')).toBeNull();
  fireEvent.press(getByTestId('tile'));
  expect(onPress).toHaveBeenCalledTimes(1);
  expect(getByTestId('tile').props.accessibilityLabel).toBe('Tears of Steel. 1 descriptions.');
});
