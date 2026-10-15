import React, {useEffect, useRef, useState} from 'react';
import {Animated, Easing, StyleSheet, Text, View} from 'react-native';

import {clock, secs} from '../format';
import {cueWindow} from '../player/schedule.js';
import type {Cue} from '../player/track';
import {font, line, palette, size, u} from '../theme';

/**
 * What is being said, right now.
 *
 * This is the product, so it is given the weight of a product rather than the
 * weight of a status line. It sits under the picture like a caption, on solid
 * ground, with a yellow bar beside it only while the voice is speaking. A cue arrives from below and at full brightness,
 * then settles back a shade once the voice has stopped, which is the shape of
 * being spoken to: present, then past. The panel is never empty. The last thing
 * said stays up, labelled as the last thing said, because a box that blanks out
 * between descriptions reads as a thing that is broken rather than a thing that
 * is listening.
 *
 * It is deliberately not an accessibility live region. A screen reader user is
 * already hearing this text in the app's own voice, from a real audio track
 * placed in a real gap. Announcing it a second time would talk over the film
 * at exactly the moment the whole system exists to keep quiet.
 */
/** Longer than this, a description steps down a size so it fits in three lines. */
const LONG = 100;

export const Voice = ({
  speaking, next, enabled, time, hint,
}: {
  speaking: Cue | null;
  next: Cue | null;
  enabled: boolean;
  time: number;
  /** What the remote can do here, said quietly beside the label. */
  hint?: string;
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

  // The scheduler points at the last cue once the film is past all of them,
  // which is right for the timeline and wrong for a sentence with the word
  // "next" in it.
  const upcoming = next !== null && next.start > time ? next : null;
  const nothingLeft =
    next === null
      ? 'No descriptions in this film.'
      : 'Nothing left to describe in this film.';

  let eyebrow = 'Waiting for a gap';
  let foot = upcoming
    ? `The film has the floor. Next description at ${clock(upcoming.start)}.`
    : nothingLeft;
  if (!enabled) {
    eyebrow = 'Description off';
    foot = 'The film is playing with its own sound and nothing else.';
  } else if (speaking) {
    eyebrow = 'aloud is describing';
    foot = window
      ? `Inside ${secs(window.silence)} of quiet, with ${secs(window.spare)} of it still to come when the voice stops.`
      : '';
  } else if (shown) {
    eyebrow = 'Just said';
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
    <View style={styles.area} testID="cue-area">
      <View style={styles.rail}>
        <Animated.View style={[styles.railLit, {opacity: lit}]} />
      </View>

      <View style={styles.body}>
        <View style={styles.eyebrowRow}>
          <Text style={[styles.eyebrow, speaking !== null && styles.eyebrowLive]}>
            {eyebrow}
          </Text>
          {hint ? <Text style={styles.hint}>{hint}</Text> : null}
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
                    outputRange: [u(16), 0],
                  }),
                },
              ],
            }}>
            <Text style={[styles.cue, shown.text.length > LONG && styles.cueLong]}
                  testID="cue-text">
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

        {/* A long sentence takes the room the footnote would have used. */}
        {shown && shown.text.length > LONG ? null : (
          <Text style={styles.foot} numberOfLines={1}>{foot}</Text>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  // No panel and no card: the description is set on the ground under the
  // film, like a caption, so nothing on the screen competes with the picture.
  area: {flexDirection: 'row'},
  // The voice colour appears only while the voice is speaking.
  rail: {width: u(8), backgroundColor: palette.line, marginRight: u(26)},
  railLit: {position: 'absolute', top: 0, bottom: 0, left: 0, right: 0,
            backgroundColor: palette.voice},
  body: {flex: 1},

  eyebrowRow: {flexDirection: 'row', justifyContent: 'space-between'},
  hint: {...font.regular, color: palette.inkMuted, fontSize: size.label,
         lineHeight: line.label},
  eyebrow: {...font.semibold, color: palette.inkMuted, fontSize: size.label,
            lineHeight: line.label},
  eyebrowLive: {color: palette.voice},

  cue: {...font.semibold, color: palette.ink, fontSize: size.cue, lineHeight: line.cue},
  cueLong: {fontSize: u(36), lineHeight: u(46)},
  idle: {...font.regular, color: palette.inkMuted, fontSize: size.body,
         lineHeight: line.body, marginTop: u(10)},

  foot: {...font.regular, color: palette.inkMuted, fontSize: size.label,
         lineHeight: line.label, marginTop: u(8)},
});
