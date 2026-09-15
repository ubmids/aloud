import React, {useEffect, useRef, useState} from 'react';
import {Animated, Easing, StyleSheet, Text, View} from 'react-native';
import type {DimensionValue} from 'react-native';

import {clock, secs} from '../format';
import {cueWindow} from '../player/schedule.js';
import type {Cue} from '../player/track';
import {palette, size, u} from '../theme';

/**
 * What is being said, right now.
 *
 * This is the product, so it is given the weight of a product rather than the
 * weight of a status line. A cue arrives from below and at full brightness,
 * then settles back a shade once the voice has stopped, which is the shape of
 * being spoken to: present, then past. The panel is never empty. The last thing
 * said stays up, labelled as the last thing said, because a box that blanks out
 * between descriptions reads as a thing that is broken rather than a thing that
 * is listening.
 *
 * Underneath the words, a rule fills as the speech plays and stops short of
 * the end of the silence. That is the same fact the timeline lens is making,
 * at the scale of one sentence, and it is the reason the rule is there rather
 * than a level meter: a meter would be decoration, invented from nothing, while
 * this is the description's own progress against its own deadline.
 *
 * It is deliberately not an accessibility live region. A screen reader user is
 * already hearing this text in the app's own voice, from a real audio track
 * placed in a real gap. Announcing it a second time would talk over the film
 * at exactly the moment the whole system exists to keep quiet.
 */
export const Voice = ({
  speaking, next, enabled, time,
}: {
  speaking: Cue | null;
  next: Cue | null;
  enabled: boolean;
  time: number;
}) => {
  const [last, setLast] = useState<Cue | null>(null);
  const enter = useRef(new Animated.Value(1)).current;
  const lit = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!speaking) return;
    setLast(speaking);
    enter.setValue(0);
    Animated.timing(enter, {
      toValue: 1,
      duration: 260,
      easing: Easing.out(Easing.cubic),
      // Opacity and translate only, so the whole transition runs on the UI
      // thread and cannot be stuttered by the timeupdate handler landing in
      // the middle of it.
      useNativeDriver: true,
    }).start();
  }, [speaking, enter]);

  useEffect(() => {
    Animated.timing(lit, {
      toValue: speaking ? 1 : 0,
      duration: 300,
      useNativeDriver: true,
    }).start();
  }, [speaking, lit]);

  // Turning description off clears the panel rather than leaving the last thing
  // said sitting under a label that says the feature is off.
  useEffect(() => {
    if (!enabled) setLast(null);
  }, [enabled]);

  const shown = enabled ? last : null;
  const window = shown ? cueWindow(shown) : null;
  const said =
    speaking && window
      ? Math.max(0, Math.min(1, (time - speaking.start) / window.speech))
      : 1;

  // The scheduler points at the last cue once the film is past all of them,
  // which is right for the timeline and wrong for a sentence with the word
  // "next" in it.
  const upcoming = next !== null && next.start > time ? next : null;
  const nothingLeft =
    next === null
      ? 'No descriptions in this film.'
      : 'Nothing left to describe in this film.';

  let eyebrow = 'WAITING FOR A GAP';
  let foot = upcoming
    ? `The film has the floor. Next description at ${clock(upcoming.start)}.`
    : nothingLeft;
  if (!enabled) {
    eyebrow = 'DESCRIPTION OFF';
    foot = 'The film is playing with its own sound and nothing else.';
  } else if (speaking) {
    eyebrow = 'SPEAKING NOW';
    foot = window
      ? `Inside ${secs(window.silence)} of quiet, with ${secs(window.spare)} of it still to come when the voice stops.`
      : '';
  } else if (shown) {
    eyebrow = 'JUST SAID';
    // The gap it fitted, and then what is coming, because between descriptions
    // is where this panel spends most of a film and a viewer who is told
    // nothing is waiting is a viewer who thinks it has stopped working.
    const fitted = window
      ? `It fitted a ${secs(window.silence)} gap and left ${secs(window.spare)} of quiet behind it.`
      : '';
    foot = upcoming
      ? `${fitted} Next description at ${clock(upcoming.start)}.`
      : `${fitted} That was the last one.`;
  }

  return (
    <View style={styles.panel} testID="cue-area">
      <View style={styles.rail}>
        <Animated.View style={[styles.railLit, {opacity: lit}]} />
      </View>

      <View style={styles.body}>
        <View style={styles.eyebrowRow}>
          <Animated.View
            style={[
              styles.dot,
              {opacity: lit.interpolate({inputRange: [0, 1], outputRange: [0.35, 1]})},
            ]}
          />
          <Text style={styles.eyebrow}>{eyebrow}</Text>
        </View>

        {shown ? (
          <Animated.View
            style={{
              opacity: Animated.multiply(
                enter,
                lit.interpolate({inputRange: [0, 1], outputRange: [0.82, 1]}),
              ),
              transform: [
                {
                  translateY: enter.interpolate({
                    inputRange: [0, 1],
                    outputRange: [u(22), 0],
                  }),
                },
              ],
            }}>
            <Text style={styles.cue} testID="cue-text">
              {shown.text}
            </Text>
          </Animated.View>
        ) : (
          <Text style={styles.idle}>
            {enabled
              ? 'Listening for the next gap in the dialogue.'
              : 'Nothing is being described.'}
          </Text>
        )}

        <View style={styles.progress}>
          <View
            style={[
              styles.progressFill,
              {width: `${said * 100}%` as DimensionValue},
              speaking !== null && styles.progressLit,
            ]}
          />
        </View>

        <Text style={styles.foot}>{foot}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  // A fixed width rather than a share of the row, so the film keeps a
  // sixteen by nine shape close to its own and the description keeps a
  // measure that does not run to fifty characters a line.
  panel: {width: u(780), marginLeft: u(28), flexDirection: 'row',
          borderRadius: u(14),
          backgroundColor: palette.panel, borderWidth: u(2),
          borderColor: palette.edge, overflow: 'hidden'},
  // A vertical rule rather than a coloured background, so the panel does not
  // glow at the film sitting next to it.
  rail: {width: u(10), backgroundColor: palette.voiceDim},
  railLit: {position: 'absolute', top: u(0), bottom: u(0), left: u(0), right: u(0),
            backgroundColor: palette.voice},
  body: {flex: 1, paddingHorizontal: u(32), paddingVertical: u(26),
         justifyContent: 'center'},

  eyebrowRow: {flexDirection: 'row', alignItems: 'center', marginBottom: u(18)},
  dot: {width: u(14), height: u(14), borderRadius: u(7), marginRight: u(12),
        backgroundColor: palette.voice},
  eyebrow: {color: palette.voice, fontSize: size.eyebrow, letterSpacing: u(4),
            fontWeight: '700'},

  cue: {color: palette.ink, fontSize: size.cue, lineHeight: u(48),
        fontWeight: '500'},
  idle: {color: palette.inkMuted, fontSize: size.lead, lineHeight: u(36)},

  progress: {height: u(6), borderRadius: u(3), backgroundColor: palette.edge,
             marginTop: u(24), overflow: 'hidden'},
  progressFill: {height: u(6), borderRadius: u(3), backgroundColor: palette.voiceDim},
  progressLit: {backgroundColor: palette.voice},

  foot: {color: palette.inkMuted, fontSize: size.body, lineHeight: u(28),
         marginTop: u(18)},
});
