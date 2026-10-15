import React from 'react';
import {StyleSheet, View, type DimensionValue} from 'react-native';

import {cueWindow} from '../player/schedule.js';
import type {Cue} from '../player/track';
import {palette} from '../theme';

/**
 * A film's speech, drawn: dialogue as a mid-tone bar, each silence a description
 * was placed in cut out of it, and the description sitting inside the silence.
 *
 * Used at two sizes: as the player's schedule, with a playhead and the cue
 * being spoken lit to full height, and under each tile on the shelf, where it
 * is the film's fingerprint. Every block is a cue from the track; nothing here
 * is decoration.
 */
export const GapStrip = ({
  cues, span, height, speaking = null, now = null, testID,
}: {
  cues: Cue[];
  /** Seconds the strip covers, from zero. */
  span: number;
  height: number;
  speaking?: Cue | null;
  now?: number | null;
  testID?: string;
}) => {
  const total = span > 0 ? span : 1;
  // React Native types a percentage as a `${number}%` template literal.
  const pct = (v: number): DimensionValue =>
    `${Math.max(0, Math.min(100, v * 100))}%` as DimensionValue;
  return (
    <View style={[styles.track, {height}]} testID={testID}>
      {cues.map((cue) => {
        const w = cueWindow(cue);
        const live = speaking !== null && speaking.start === cue.start;
        return (
          <View
            key={cue.start}
            testID={testID ? `cue-block-${cue.start}` : undefined}
            style={[styles.silence, {left: pct(w.opens / total),
                                     width: pct(w.silence / total)}]}>
            <View
              style={[
                styles.voice,
                live ? styles.voiceLive : styles.voicePlaced,
                {left: pct((w.start - w.opens) / w.silence),
                 width: pct(w.speech / w.silence)},
              ]}
            />
          </View>
        );
      })}
      {now !== null ? (
        <View style={[styles.playhead, {left: pct(now / total)}]} testID="playhead" />
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  track: {backgroundColor: palette.dialogue, overflow: 'hidden'},
  // A silence is a hole in the dialogue rather than a shape on top of it,
  // because that is what it is.
  silence: {position: 'absolute', top: 0, bottom: 0, minWidth: 2,
            backgroundColor: palette.recess},
  voice: {position: 'absolute', backgroundColor: palette.voice},
  voicePlaced: {top: '30%', bottom: '30%'},
  voiceLive: {top: 0, bottom: 0},
  playhead: {position: 'absolute', top: 0, bottom: 0, width: 3, marginLeft: -1,
             backgroundColor: palette.ink},
});
