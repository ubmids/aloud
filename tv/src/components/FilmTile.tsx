import React, {useEffect, useRef, useState} from 'react';
import {Animated, Easing, Image, Pressable, StyleSheet, Text, View} from 'react-native';

import type {Film} from '../film';
import {palette, size, u} from '../theme';

/**
 * One film on the shelf.
 *
 * Focus is the loudest thing on the screen, for the same reason as the
 * settings: it is read from a sofa, and for a low vision viewer it may be the
 * only thing read at all. The focused tile lifts, takes a thick accent ring,
 * and says what select will do. Unfocused tiles dim rather than disappear, so
 * the row still reads as a row.
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
      duration: 160,
      easing: Easing.out(Easing.quad),
      useNativeDriver: true,
    }).start();
  }, [focused, rise]);

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
          focused && styles.tileFocused,
          {
            opacity: rise.interpolate({inputRange: [0, 1], outputRange: [0.72, 1]}),
            transform: [
              {scale: rise.interpolate({inputRange: [0, 1], outputRange: [1, 1.07]})},
            ],
          },
        ]}>
        <Image source={film.poster} style={styles.poster} resizeMode="cover" />
        <View style={styles.caption}>
          <Text style={styles.title} numberOfLines={1}>{film.title}</Text>
          <Text style={[styles.cta, focused && styles.ctaFocused]}>
            {focused ? 'PRESS SELECT TO PLAY' : `${film.track.cues.length} DESCRIPTIONS`}
          </Text>
        </View>
      </Animated.View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  tile: {width: u(400), marginRight: u(32), borderRadius: u(14),
         borderWidth: u(4), borderColor: palette.edge,
         backgroundColor: palette.panel, overflow: 'hidden'},
  tileFocused: {borderColor: palette.voice},
  poster: {width: '100%', height: u(168)},
  caption: {paddingHorizontal: u(20), paddingVertical: u(14)},
  title: {color: palette.ink, fontSize: size.lead, fontWeight: '600'},
  cta: {color: palette.inkMuted, fontSize: size.eyebrow, letterSpacing: u(3),
        marginTop: u(6)},
  ctaFocused: {color: palette.voice},
});
