import React, {useState} from 'react';
import {Pressable, StyleSheet, Text, View} from 'react-native';

/**
 * A focusable control for a remote.
 *
 * A television is operated from across a room with five buttons, so the focused
 * state has to be obvious at three metres and the label has to say what the
 * setting means rather than what it is called. "Only what changed most" tells a
 * viewer what they will get; "sparse" tells them nothing.
 */
export const Toggle = ({
  label, value, onPress, hasTVPreferredFocus, testID,
}: {
  label: string;
  value: string;
  onPress: () => void;
  hasTVPreferredFocus?: boolean;
  testID?: string;
}) => {
  const [focused, setFocused] = useState(false);
  return (
    <Pressable
      onPress={onPress}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      hasTVPreferredFocus={hasTVPreferredFocus}
      testID={testID}
      style={[styles.box, focused && styles.boxFocused]}>
      <View>
        <Text style={[styles.label, focused && styles.labelFocused]}>
          {label.toUpperCase()}
        </Text>
        <Text style={[styles.value, focused && styles.valueFocused]}>
          {value}
        </Text>
      </View>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  box: {borderRadius: 10, borderWidth: 1, borderColor: '#302722',
        backgroundColor: '#161110', paddingHorizontal: 22, paddingVertical: 14,
        marginRight: 16, minWidth: 220},
  boxFocused: {borderColor: '#ff7a45', backgroundColor: '#241a15'},
  label: {color: '#6f5f54', fontSize: 12, letterSpacing: 3},
  labelFocused: {color: '#ff7a45'},
  value: {color: '#f2e9e1', fontSize: 22, marginTop: 4},
  valueFocused: {color: '#ffffff'},
});
