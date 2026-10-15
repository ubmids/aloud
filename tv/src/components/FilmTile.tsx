import React, {useEffect, useRef, useState} from 'react';
import {Animated, Easing, Image, Pressable, StyleSheet, Text, View} from 'react-native';

import type {Film} from '../film';
import {GapStrip} from './GapStrip';
import {focus, font, line, palette, size, u} from '../theme';

/** "1 description", "47 descriptions". */
export const descriptions = (n: number) => `${n} description${n === 1 ? '' : 's'}`;

/**
 * One film on the shelf.
 *
 * Focus is the loudest thing on the screen, because it is read from a sofa
 * and for a low-vision viewer it may be the only thing read at all. Three
 * things change at once, so no single cue has to carry it: a thick ink frame,
 * the title bar inverting to ink, and a small lift. Unfocused tiles stay at
 * full strength; dimming them would make the row harder to read for exactly
 * the viewers it is for.
 *
 * Under the title, the film's fingerprint: its descriptions drawn where they
 * sit, from the track, so a film with no dialogue (Big Buck Bunny) visibly
 * carries more.
 */
export const FilmTile = ({
  film, label, onFocus, onPress, hasTVPreferredFocus, testID,
}: {
  film: Film;
  /** Everything a screen reader should say about this title. */
  label: string;
  onFocus: () => void;
  onPress: () => void;
  hasTVPreferredFocus?: boolean;
  testID?: string;
}) => {
  const [focused, setFocused] = useState(false);
  const rise = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(rise, {
      toValue: focused ? 1 : 0,
      duration: focus.ms,
      easing: Easing.out(Easing.quad),
      useNativeDriver: true,
    }).start();
  }, [focused, rise]);

  const cues = film.track.cues;
  const span = Math.max(film.minutes * 60, cues.at(-1)?.end ?? 0);

  return (
    <Pressable
      onPress={onPress}
      onFocus={() => {
        setFocused(true);
        onFocus();
      }}
      onBlur={() => setFocused(false)}
      hasTVPreferredFocus={hasTVPreferredFocus}
      testID={testID}
      accessible
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityHint="Press select to play with descriptions.">
      <Animated.View
        style={[
          styles.tile,
          {transform: [{scale: rise.interpolate({inputRange: [0, 1],
                                                 outputRange: [1, focus.lift]})}]},
        ]}>
        <Image source={film.poster} style={styles.poster} resizeMode="cover" />
        <View style={[styles.bar, focused && styles.barFocused]}>
          <Text style={[styles.title, focused && styles.inverted]} numberOfLines={1}>
            {film.title}
          </Text>
          <Text style={[styles.sub, focused && styles.subFocused]}>
            {focused ? 'Select to play' : descriptions(cues.length)}
          </Text>
          <View style={styles.print}>
            <GapStrip cues={cues} span={span} height={u(10)} />
          </View>
        </View>
        {/* The frame sits over the tile rather than around it, so taking
            focus moves nothing else on the shelf. */}
        <Animated.View pointerEvents="none" style={[styles.frame, {opacity: rise}]} />
      </Animated.View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  tile: {width: u(352), marginRight: u(32), backgroundColor: palette.raised},
  poster: {width: u(352), height: u(198)},
  bar: {paddingHorizontal: u(18), paddingTop: u(10), paddingBottom: u(14)},
  barFocused: {backgroundColor: palette.ink},
  title: {...font.semibold, color: palette.ink, fontSize: size.body, lineHeight: u(34)},
  sub: {...font.mono, color: palette.inkMuted, fontSize: size.label, lineHeight: line.label},
  inverted: {color: palette.ground},
  subFocused: {...font.semibold, color: palette.ground},
  print: {marginTop: u(8)},
  frame: {position: 'absolute', top: -focus.frame, left: -focus.frame,
          right: -focus.frame, bottom: -focus.frame,
          borderWidth: focus.frame, borderColor: palette.ink},
});
