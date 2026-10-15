import React, {useEffect, useRef, useState} from 'react';
import {Animated, Easing, Pressable, StyleSheet, Text} from 'react-native';

import {focus, font, line, palette, size, u} from '../theme';

/**
 * A setting, operated from a sofa with five buttons.
 *
 * Two rules, both of them about distance. Focus has to be unmistakable from
 * three metres and in greyscale, so the focused control changes three things
 * at once: it inverts to ink, takes a frame, and lifts. A control that
 * announced focus with a slightly lighter border would be a control nobody
 * could find.
 *
 * And a setting has to say what it does rather than what it is called. "Only
 * what changed most" is a choice a person can make. "Sparse" is a parameter
 * name that leaked into the product. The help line under each value exists for
 * the same reason: a viewer deciding how much description they want is not
 * configuring software.
 */
export const Toggle = ({
  label, value, help, onPress, checked, hasTVPreferredFocus, testID, spoken, speak,
  width = u(400),
}: {
  label: string;
  value: string;
  help: string;
  onPress: () => void;
  /** Present when the setting is genuinely on or off, absent when it is a
   *  choice between two named amounts. It decides what a screen reader calls
   *  the control, which should not be guessed from the label. */
  checked?: boolean;
  hasTVPreferredFocus?: boolean;
  testID?: string;
  /** The clip that says this setting's name and current value. */
  spoken?: string;
  /** Plays a clip, or decides not to (VoiceView on, menu voice off). */
  speak?: (uri: string) => void;
  width?: number;
}) => {
  const [focused, setFocused] = useState(false);
  const rise = useRef(new Animated.Value(0)).current;

  // Said on focus, and again once select has changed the value, so the viewer
  // hears what they just chose. Only a press here is answered: a value the
  // app changes by itself (Menu asked twice, say) must not talk over a
  // description or a line of the film.
  const pressed = useRef(false);
  const said = useRef(spoken);
  useEffect(() => {
    if (pressed.current && spoken && spoken !== said.current) speak?.(spoken);
    pressed.current = false;
    said.current = spoken;
  }, [spoken, speak]);

  useEffect(() => {
    Animated.timing(rise, {
      toValue: focused ? 1 : 0,
      duration: focus.ms,
      easing: Easing.out(Easing.quad),
      // Every style this value drives is opacity or transform, which is what
      // lets it run on the UI thread. That is also why the frame fades in at a
      // fixed width rather than growing: animating a width would drag the
      // whole control back onto the JavaScript thread.
      useNativeDriver: true,
    }).start();
  }, [focused, rise]);

  return (
    <Pressable
      onPress={() => {
        pressed.current = true;
        onPress();
      }}
      onFocus={() => {
        setFocused(true);
        if (spoken) speak?.(spoken);
      }}
      onBlur={() => setFocused(false)}
      hasTVPreferredFocus={hasTVPreferredFocus}
      testID={testID}
      accessible
      accessibilityRole={checked === undefined ? 'button' : 'switch'}
      accessibilityState={checked === undefined ? undefined : {checked}}
      accessibilityLabel={`${label}. ${value}. ${help}`}
      accessibilityHint="Press select to change this setting.">
      <Animated.View
        style={[
          styles.box,
          {width},
          focused && styles.boxFocused,
          {
            transform: [
              {scale: rise.interpolate({inputRange: [0, 1], outputRange: [1, focus.lift]})},
            ],
          },
        ]}>
        <Text style={[styles.label, focused && styles.onInk]}>{label}</Text>
        <Text style={[styles.value, focused && styles.onInk]}>{value}</Text>
        <Text style={[styles.help, focused && styles.onInk]}>{help}</Text>
        {/* Over the control, not around it, so focus moves nothing else. */}
        <Animated.View pointerEvents="none" style={[styles.frame, {opacity: rise}]} />
      </Animated.View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  // Square and separated by tone, not outlined: a setting is a surface, not a
  // card.
  box: {backgroundColor: palette.raised, paddingHorizontal: u(22),
        paddingTop: u(12), paddingBottom: u(14), marginRight: u(24)},
  boxFocused: {backgroundColor: palette.ink},
  label: {...font.semibold, color: palette.inkMuted, fontSize: size.label,
          lineHeight: line.label},
  value: {...font.semibold, color: palette.ink, fontSize: size.lead,
          lineHeight: line.lead},
  help: {...font.regular, color: palette.inkSoft, fontSize: size.label,
         lineHeight: line.label, marginTop: u(2)},
  onInk: {color: palette.ground},
  // Held off the fill by a dark gutter, so the frame reads as a frame and not
  // as a slightly bigger box.
  frame: {position: 'absolute', top: -(focus.frame + u(6)), left: -(focus.frame + u(6)),
          right: -(focus.frame + u(6)), bottom: -(focus.frame + u(6)),
          borderWidth: focus.frame, borderColor: palette.ink},
});
