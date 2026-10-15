import React from 'react';
import {StyleSheet, Text, View} from 'react-native';

import {clock, secs} from '../format';
import {cueWindow, nextCueFrom} from '../player/schedule.js';
import type {Cue} from '../player/track';
import {GapStrip} from './GapStrip';
import {font, line, palette, size, u} from '../theme';

/**
 * The schedule, drawn, and the largest thing on the screen after the film.
 *
 * Audio description is invisible. A still of this app playing a film is a still
 * of the film, and the one claim the whole system rests on, that a description
 * never lands on a line, is otherwise something a viewer has to take on trust.
 * So the screen shows the shape of the film's own speech, the silences cut into
 * it, and the description sitting inside one.
 *
 * The strip is the whole film, where the point is how rarely the voice speaks
 * and how evenly the gaps are spread. Under it, one sentence gives the margin
 * for the gap the viewer is in: how much quiet there was and how much of it
 * the description used. It is the evidence, so it is kept small: nothing on
 * the player is louder than the film.
 *
 * Three states, and none of them is told by hue alone. Dialogue is a mid-tone
 * fill, a silence is a recess cut into it, a description is the one bright
 * thing (3.3:1 and 4.2:1 apart), and the legend names all three in words.
 *
 * It is deliberately not a scrubber. Nobody needs to seek by description.
 */
export const Timeline = ({
  duration, cues, current, speaking,
}: {
  duration: number;
  cues: Cue[];
  current: number;
  speaking: Cue | null;
}) => {
  const span = duration > 0 ? duration : 1;

  const marks = cues.map((cue, i) => ({cue, number: i + 1, w: cueWindow(cue)}));
  // The gap the viewer is in, or the one they are waiting for. The scheduler
  // answers this, because "which cue is current" is the same question it asks
  // itself four times a second and it should only be answered in one place.
  const focus = nextCueFrom(cues, current);
  const lens = marks.find((m) => m.cue === focus) ?? marks[0];
  // The scheduler hands back its own normalised copy of a cue, so identity is
  // no use here and the start time is the identifier.
  const live = speaking !== null && lens !== undefined &&
    speaking.start === lens.cue.start;

  return (
    <View
      testID="timeline"
      accessible
      accessibilityLabel={
        `Where the descriptions sit. ${cues.length} descriptions placed in ` +
        `gaps in the dialogue, across ${clock(span)}. Now at ${clock(current)}.` +
        (lens
          ? ` Gap ${lens.number}: ${secs(lens.w.silence)} of quiet holding ` +
            `${secs(lens.w.speech)} of description, ${secs(lens.w.spare)} to spare.`
          : '')
      }>
      <GapStrip cues={cues} span={span} height={STRIP} speaking={speaking}
                now={current} />

      <View style={styles.under}>
        <Text style={styles.time}>{clock(current)}</Text>
        {lens ? (
          <Text style={[styles.lens, live && styles.lensLive]} testID="lens"
                numberOfLines={1}>
            {`Gap ${lens.number} of ${marks.length}: ${secs(lens.w.speech)} of ` +
             `description in ${secs(lens.w.silence)} of quiet`}
          </Text>
        ) : <View style={styles.lensSpacer} />}
        <View style={styles.legend}>
          <Key mark={styles.keyDialogue} text="talking" />
          <Key mark={styles.keySilence} text="quiet" />
          <Key mark={styles.keyVoice} text="aloud" />
        </View>
        <Text style={styles.time}>{clock(span)}</Text>
      </View>
    </View>
  );
};

const Key = ({mark, text}: {mark: object; text: string}) => (
  <View style={styles.key}>
    <View style={[styles.keyMark, mark]} />
    <Text style={styles.keyText}>{text}</Text>
  </View>
);

const STRIP = u(32);

const styles = StyleSheet.create({
  under: {flexDirection: 'row', alignItems: 'center', marginTop: u(8)},
  time: {...font.mono, color: palette.inkMuted, fontSize: size.label,
         lineHeight: line.label},
  lens: {...font.regular, color: palette.inkSoft, fontSize: size.label,
         lineHeight: line.label, marginLeft: u(32), flexShrink: 1},
  lensLive: {color: palette.ink},
  lensSpacer: {flex: 1},
  legend: {flexDirection: 'row', marginLeft: 'auto', marginRight: u(32)},
  key: {flexDirection: 'row', alignItems: 'center', marginLeft: u(24)},
  keyMark: {width: u(24), height: u(16), marginRight: u(8)},
  keyDialogue: {backgroundColor: palette.dialogue},
  keySilence: {backgroundColor: palette.recess, borderWidth: u(2),
               borderColor: palette.line},
  keyVoice: {backgroundColor: palette.voice},
  keyText: {...font.regular, color: palette.inkMuted, fontSize: size.label,
            lineHeight: line.label},
});
