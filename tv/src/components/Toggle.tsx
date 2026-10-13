import React, {useEffect, useRef, useState} from 'react';
import {Animated, Easing, Pressable, StyleSheet, Text} from 'react-native';

import {palette, size, u} from '../theme';

/**
 * A setting, operated from a sofa with five buttons.
 *
 * Two rules, both of them about distance. Focus has to be unmistakable from
 * three metres, so the focused control lifts: it scales up, grows an accent
 * edge, and reveals the one instruction a remote user needs. A control that
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
      duration: 160,
      easing: Easing.out(Easing.quad),
      // Every style this value drives is opacity or transform, which is what
      // lets it run on the UI thread. That is also why the accent edge fades
      // in at a fixed width rather than growing: animating a width would drag
      // the whole control back onto the JavaScript thread for no more signal
      // than the lift already gives.
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
          focused && styles.boxFocused,
          {
            transform: [
              {scale: rise.interpolate({inputRange: [0, 1], outputRange: [1, 1.05]})},
            ],
          },
        ]}>
        <Animated.View style={[styles.edge, {opacity: rise}]} />
        <Text style={styles.label}>{label.toUpperCase()}</Text>
        <Text style={[styles.value, focused && styles.valueFocused]}>{value}</Text>
        <Text style={styles.help}>{help}</Text>
        <Animated.Text style={[styles.hint, {opacity: rise}]}>
          PRESS SELECT TO CHANGE
        </Animated.Text>
      </Animated.View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  box: {borderRadius: u(14), borderWidth: u(2), borderColor: palette.edge,
        backgroundColor: palette.panel, paddingLeft: u(28), paddingRight: u(24),
        paddingVertical: u(18), marginRight: u(28), width: u(400), overflow: 'hidden'},
  boxFocused: {borderColor: palette.voice, backgroundColor: palette.voiceWash},
  edge: {position: 'absolute', left: u(0), top: u(0), bottom: u(0), width: u(10),
         backgroundColor: palette.voice},
  label: {color: palette.inkMuted, fontSize: size.eyebrow, letterSpacing: u(3)},
  value: {color: palette.ink, fontSize: u(30), marginTop: u(6), fontWeight: '600'},
  valueFocused: {color: palette.voice},
  help: {color: palette.inkSoft, fontSize: size.eyebrow, lineHeight: u(24),
         marginTop: u(8)},
  // Always laid out, only ever faded in, so nothing below it moves when focus
  // arrives. The control lifting is the signal; the row underneath it jumping
  // would be noise.
  hint: {color: palette.voice, fontSize: size.eyebrow, letterSpacing: u(3),
         marginTop: u(10), height: u(22)},
});
