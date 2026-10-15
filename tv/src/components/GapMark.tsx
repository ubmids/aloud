import React from 'react';
import {StyleSheet, View} from 'react-native';

import {palette, u} from '../theme';

/**
 * aloud's mark: two lines of dialogue with a silence between them, and the
 * voice fitted inside it. It is the whole product at the size of a letter, so
 * it is the logo, and it is drawn rather than loaded so it scales with the
 * type beside it.
 */
export const GapMark = ({height = 34}: {height?: number}) => {
  const k = height / 34;
  return (
    <View style={styles.row} accessible={false} importantForAccessibility="no">
      <View style={[styles.dialogue, {width: u(30 * k), height: u(20 * k)}]} />
      <View style={[styles.voice, {width: u(30 * k), height: u(34 * k),
                                   marginHorizontal: u(6 * k)}]} />
      <View style={[styles.dialogue, {width: u(18 * k), height: u(20 * k)}]} />
    </View>
  );
};

const styles = StyleSheet.create({
  row: {flexDirection: 'row', alignItems: 'center'},
  dialogue: {backgroundColor: palette.dialogue},
  voice: {backgroundColor: palette.voice},
});
