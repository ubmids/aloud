import React from 'react';
import {StyleSheet, Text, View, type DimensionValue} from 'react-native';

import type {Cue} from '../player/track';

/**
 * The schedule, drawn.
 *
 * Every block is a description sitting inside a gap in the dialogue. The point
 * of drawing it is that the safety claim of this whole system, that a
 * description never lands on a line, is otherwise something a viewer has to
 * take on trust. Here they can watch the playhead cross a block and hear the
 * description start, and watch it cross the space between blocks and hear
 * dialogue instead.
 *
 * It is deliberately not a scrubber. Nobody needs to seek by description.
 */
export const Timeline = ({
  duration, cues, current, speakingId,
}: {
  duration: number;
  cues: Cue[];
  current: number;
  speakingId: string | null;
}) => {
  const span = duration > 0 ? duration : 1;
  // React Native types a percentage as a `${number}%` template literal, so the
  // cast is the type system asking for a promise the clamp above already keeps.
  const pct = (v: number): DimensionValue =>
    `${Math.max(0, Math.min(100, (v / span) * 100))}%` as DimensionValue;

  return (
    <View testID="timeline">
      <Text style={styles.caption}>
        WHERE THE DESCRIPTIONS SIT · {cues.length} in {Math.round(span)}s
      </Text>
      <View style={styles.track}>
        {cues.map((c) => (
          <View
            key={`${c.start}-${c.end}`}
            testID={`cue-block-${c.start}`}
            style={[
              styles.cue,
              {left: pct(c.start), width: pct(c.end - c.start)},
              speakingId === `${c.start}` && styles.cueSpeaking,
            ]}
          />
        ))}
        <View style={[styles.playhead, {left: pct(current)}]} testID="playhead" />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  caption: {color: '#6f5f54', fontSize: 12, letterSpacing: 3, marginBottom: 8},
  track: {height: 30, borderRadius: 6, backgroundColor: '#161110',
          borderWidth: 1, borderColor: '#241d19', position: 'relative',
          overflow: 'hidden'},
  cue: {position: 'absolute', top: 0, bottom: 0, backgroundColor: '#8a3f22',
        borderRadius: 4},
  cueSpeaking: {backgroundColor: '#ff7a45'},
  playhead: {position: 'absolute', top: -4, bottom: -4, width: 2,
             backgroundColor: '#f2e9e1'},
});
