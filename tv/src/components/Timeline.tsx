import React from 'react';
import {StyleSheet, Text, View, type DimensionValue} from 'react-native';

import {clock, secs} from '../format';
import {cueWindow, nextCueFrom} from '../player/schedule.js';
import type {Cue} from '../player/track';
import {palette, size, u} from '../theme';

/**
 * The schedule, drawn, and the largest thing on the screen after the film.
 *
 * Audio description is invisible. A still of this app playing a film is a still
 * of the film, and the one claim the whole system rests on, that a description
 * never lands on a line, is otherwise something a viewer has to take on trust.
 * So the screen shows the shape of the film's own speech, the silences cut into
 * it, and the description sitting inside one.
 *
 * It is drawn at two scales on purpose, because one scale cannot carry both
 * facts. The strip is the whole film, where the point is how rarely the voice
 * speaks and how evenly the gaps are spread. Underneath it, one silence is
 * blown up to the full width, where the point is the margin: the voice starts
 * after the dialogue stops and finishes with quiet still to spare. At film
 * scale that margin is four pixels. At gap scale it is the product.
 *
 * Three states, and none of them is told by hue alone. Dialogue is a mid-tone
 * fill, a silence is a recess cut into it, a description is the one bright
 * thing, and the legend names all three in words.
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
  // React Native types a percentage as a `${number}%` template literal, so the
  // cast is the type system asking for a promise the clamp already keeps.
  const pct = (v: number): DimensionValue =>
    `${Math.max(0, Math.min(100, v * 100))}%` as DimensionValue;
  const of = (v: number) => pct(v / span);

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
      <View style={styles.head}>
        <Text style={styles.eyebrow}>WHERE EVERY DESCRIPTION SITS</Text>
        <View style={styles.legend}>
          <Key mark={styles.keyDialogue} text="someone is talking" />
          <Key mark={styles.keySilence} text="a gap in the dialogue" />
          <Key mark={styles.keyVoice} text="Aloud speaking" />
        </View>
      </View>

      <View style={styles.numbers}>
        {marks.map(({number, w}) => (
          <Text key={number} style={[styles.number, {left: of(w.opens)}]}>
            {number}
          </Text>
        ))}
      </View>

      <View style={styles.trackWrap}>
        <View style={styles.track}>
          {marks.map(({cue, number, w}) => (
            <View
              key={number}
              testID={`cue-block-${cue.start}`}
              style={[
                styles.silence,
                {left: of(w.opens), width: of(w.silence)},
              ]}>
              <View
                style={[
                  styles.voice,
                  {
                    left: pct((w.start - w.opens) / w.silence),
                    width: pct(w.speech / w.silence),
                  },
                  speaking?.start === cue.start && styles.voiceLive,
                ]}
              />
            </View>
          ))}
        </View>
        <View style={[styles.playhead, {left: of(current)}]} testID="playhead">
          <View style={styles.playheadCap} />
        </View>
      </View>

      <View style={styles.ruler}>
        <Text style={styles.rulerEnd}>0:00</Text>
        <View style={[styles.chip, {left: of(current)}]}>
          <Text style={styles.chipText}>{clock(current)}</Text>
        </View>
        <Text style={styles.rulerEnd}>{clock(span)}</Text>
      </View>

      {lens ? (
        <View style={styles.lens} testID="lens">
          {/* Two siblings rather than a nested Text, which Vega's renderer
              does not reliably lay out. */}
          <View style={styles.lensHeadRow}>
            <Text style={styles.lensHead}>
              {`GAP ${lens.number} OF ${marks.length}`}
            </Text>
            <Text style={styles.lensHeadSoft}>
              {`${secs(lens.w.silence)} of quiet, at ${clock(lens.w.opens)}`}
            </Text>
          </View>

          {/* Proportions by flex rather than by percentage, so the three parts
              of a silence always add up to it exactly and a gap with no room
              to spare draws as one with no room to spare. */}
          <View style={styles.lensBar}>
            {lens.w.start > lens.w.opens ? (
              <View
                style={[styles.lensLead, {flexGrow: lens.w.start - lens.w.opens}]}
              />
            ) : null}
            <View
              style={[
                styles.lensVoice,
                {flexGrow: lens.w.speech},
                live && styles.lensVoiceLive,
              ]}>
              <Text
                style={[styles.lensVoiceText, live && styles.lensVoiceTextLive]}
                numberOfLines={1}>
                {secs(lens.w.speech)} of description
              </Text>
            </View>
            <View style={[styles.lensSpare, {flexGrow: lens.w.spare}]}>
              <Text style={styles.lensSpareText} numberOfLines={1}>
                {secs(lens.w.spare)} still quiet
              </Text>
            </View>
          </View>

          <Text style={styles.lensFoot}>
            The voice starts after the dialogue stops and finishes before it
            comes back. That margin is the whole job.
          </Text>
        </View>
      ) : null}
    </View>
  );
};

const Key = ({mark, text}: {mark: object; text: string}) => (
  <View style={styles.key}>
    <View style={[styles.keyMark, mark]} />
    <Text style={styles.keyText}>{text}</Text>
  </View>
);

const TRACK = u(92);

const styles = StyleSheet.create({
  head: {flexDirection: 'row', alignItems: 'center', marginBottom: u(10)},
  eyebrow: {color: palette.inkSoft, fontSize: size.eyebrow, letterSpacing: u(3)},
  legend: {flexDirection: 'row', marginLeft: 'auto'},
  key: {flexDirection: 'row', alignItems: 'center', marginLeft: u(28)},
  keyMark: {width: u(26), height: u(16), borderRadius: u(3), marginRight: u(10)},
  keyDialogue: {backgroundColor: palette.dialogue},
  keySilence: {backgroundColor: palette.recess, borderWidth: u(2),
               borderColor: palette.edge},
  keyVoice: {backgroundColor: palette.voice},
  keyText: {color: palette.inkMuted, fontSize: size.eyebrow},

  numbers: {height: u(22), position: 'relative'},
  number: {position: 'absolute', color: palette.inkMuted,
           fontSize: size.eyebrow, fontWeight: '700'},

  trackWrap: {height: TRACK, position: 'relative'},
  track: {height: TRACK, borderRadius: u(8), backgroundColor: palette.dialogue,
          overflow: 'hidden'},
  // A silence is drawn as a hole in the dialogue rather than a shape on top of
  // it, because that is what it is.
  silence: {position: 'absolute', top: u(0), bottom: u(0), minWidth: u(6),
            backgroundColor: palette.recess, borderLeftWidth: u(2),
            borderRightWidth: u(2), borderColor: palette.edge},
  // Inset top and bottom so the silence is still visible around the voice. A
  // description that filled its gap edge to edge would be drawn as one that
  // fitted exactly, which is the one thing that must never be claimed.
  voice: {position: 'absolute', top: u(12), bottom: u(12), minWidth: u(4),
          borderRadius: u(5), backgroundColor: palette.voiceDim},
  voiceLive: {backgroundColor: palette.voice, top: u(6), bottom: u(6)},

  playhead: {position: 'absolute', top: u(-10), bottom: u(-10), width: u(4),
             marginLeft: u(-2), backgroundColor: palette.ink},
  playheadCap: {position: 'absolute', top: u(-14), left: u(-7), width: u(18),
                height: u(18), borderRadius: u(9), backgroundColor: palette.ink},

  ruler: {height: u(34), position: 'relative', flexDirection: 'row',
          justifyContent: 'space-between', paddingTop: u(14)},
  rulerEnd: {color: palette.inkMuted, fontSize: size.eyebrow},
  chip: {position: 'absolute', top: u(10), width: u(108), marginLeft: u(-54),
         alignItems: 'center'},
  chipText: {color: palette.ink, fontSize: size.eyebrow, fontWeight: '700',
             letterSpacing: u(1)},

  lens: {marginTop: u(6)},
  lensHeadRow: {flexDirection: 'row', alignItems: 'baseline',
                marginBottom: u(8)},
  lensHead: {color: palette.inkSoft, fontSize: size.eyebrow, letterSpacing: u(3)},
  lensHeadSoft: {color: palette.inkMuted, fontSize: size.eyebrow,
                 letterSpacing: u(1), marginLeft: u(20)},
  lensBar: {height: u(58), flexDirection: 'row', borderRadius: u(8),
            backgroundColor: palette.recess, borderWidth: u(2),
            borderColor: palette.edge, overflow: 'hidden'},
  lensLead: {flexBasis: 0},
  lensVoice: {flexBasis: 0, backgroundColor: palette.voiceDim,
              justifyContent: 'center',
              paddingHorizontal: u(16), overflow: 'hidden'},
  lensVoiceLive: {backgroundColor: palette.voice},
  lensVoiceText: {color: palette.ink, fontSize: size.eyebrow, fontWeight: '700'},
  // Ink on the lit accent measures 2.3:1 and is unreadable at any distance.
  // The bright state takes dark text; it is the only place the ink inverts.
  lensVoiceTextLive: {color: '#1b0d06'},
  lensSpare: {flexBasis: 0, justifyContent: 'center', paddingHorizontal: u(16),
              overflow: 'hidden'},
  lensSpareText: {color: palette.inkMuted, fontSize: size.eyebrow},
  lensFoot: {color: palette.inkMuted, fontSize: size.body, marginTop: u(8)},
});
