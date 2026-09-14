import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';

import {Timeline} from './components/Timeline';
import {Toggle} from './components/Toggle';
import {Speaker} from './player/speech';
import {parseTrack, totalSpokenSeconds, type Density} from './player/track';
import {useDescriptions} from './player/useDescriptions';
import demoTrack from './data/description.json';

/**
 * Aloud: a television that describes itself.
 *
 * The screen is doing something slightly unusual on purpose. Audio description
 * is invisible: a still of this app playing a film looks exactly like a still
 * of the film. So the interface shows the schedule, the gaps in the dialogue
 * and the cue currently being spoken, which makes the thing audible on screen
 * for anyone who can see it and changes nothing for the listener who cannot.
 *
 * It is also the honest surface. A viewer can see that a description was placed
 * inside a gap rather than over a line, which is the claim the whole system
 * rests on, and check it against their own ears.
 */
export const App = () => {
  const track = useMemo(() => parseTrack(demoTrack), []);
  const [density, setDensity] = useState<Density>('full');
  const [enabled, setEnabled] = useState(true);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(true);

  const speaker = useRef<Speaker | null>(null);
  if (speaker.current === null) {
    speaker.current = new Speaker();
  }
  useEffect(() => () => speaker.current?.release(), []);

  const speak = useCallback((cue: any) => {
    if (enabled) speaker.current?.speak(cue);
  }, [enabled]);
  const stop = useCallback(() => speaker.current?.stop(), []);

  const {cues, speaking, spokenCount, onTimeUpdate} = useDescriptions(
    track, density, speak, stop,
  );

  const videoRef = useRef<any>(null);

  // The only clock. Vega fires this about four times a second, which is coarse
  // against a gap of a second and a half, and the scheduler is built for that.
  const handleTimeUpdate = useCallback(() => {
    const el = videoRef.current;
    if (!el) return;
    const t = el.currentTime ?? 0;
    setTime(t);
    onTimeUpdate(t, !el.paused);
  }, [onTimeUpdate]);

  useEffect(() => {
    const el = videoRef.current;
    if (!el?.addEventListener) return;
    const onPlay = () => setPlaying(true);
    const onPause = () => {
      setPlaying(false);
      stop();
    };
    el.addEventListener('timeupdate', handleTimeUpdate);
    el.addEventListener('play', onPlay);
    el.addEventListener('pause', onPause);
    return () => {
      el.removeEventListener?.('timeupdate', handleTimeUpdate);
      el.removeEventListener?.('play', onPlay);
      el.removeEventListener?.('pause', onPause);
    };
  }, [handleTimeUpdate, stop]);

  const duration = videoRef.current?.duration || track.cues.at(-1)?.end || 0;
  const spoken = totalSpokenSeconds(cues);

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title}>Aloud</Text>
        <Text style={styles.strap}>
          A television that describes itself, in the gaps between dialogue.
        </Text>
      </View>

      <View style={styles.stage} testID="stage">
        <Text style={styles.stagePlaceholder}>
          {playing ? 'Playing' : 'Paused'} · {time.toFixed(1)}s
        </Text>
      </View>

      <View style={styles.cueArea} testID="cue-area">
        {speaking ? (
          <>
            <Text style={styles.cueLabel}>SPEAKING NOW</Text>
            <Text style={styles.cueText} testID="cue-text">
              {speaking.text}
            </Text>
          </>
        ) : (
          <Text style={styles.cueIdle}>
            {enabled
              ? 'Listening for the next gap in the dialogue.'
              : 'Description is off.'}
          </Text>
        )}
      </View>

      <Timeline
        duration={duration}
        cues={cues}
        current={time}
        speakingId={speaking ? `${speaking.start}` : null}
      />

      <TVFocusGuideView style={styles.controls}>
        <Toggle
          label="Description"
          value={enabled ? 'On' : 'Off'}
          onPress={() => {
            setEnabled((v) => !v);
            stop();
          }}
          hasTVPreferredFocus
          testID="toggle-enabled"
        />
        <Toggle
          label="How much"
          value={density === 'full' ? 'Everything' : 'Only what changed most'}
          onPress={() => setDensity((d) => (d === 'full' ? 'sparse' : 'full'))}
          testID="toggle-density"
        />
        <View style={styles.stat}>
          <Text style={styles.statLabel}>THIS FILM</Text>
          <Text style={styles.statValue}>
            {cues.length} descriptions, {spoken.toFixed(0)}s of speech
          </Text>
          <Text style={styles.statNote}>
            {spokenCount} said so far, every one inside a verified gap
          </Text>
        </View>
      </TVFocusGuideView>
    </View>
  );
};

const styles = StyleSheet.create({
  screen: {flex: 1, backgroundColor: '#0d0b0a', paddingHorizontal: 64, paddingVertical: 36},
  header: {flexDirection: 'row', alignItems: 'baseline'},
  title: {color: '#f2e9e1', fontSize: 40, fontWeight: '700', letterSpacing: -1},
  strap: {color: '#a4907f', fontSize: 20, marginLeft: 20, flexShrink: 1},
  stage: {flex: 3, marginTop: 20, borderRadius: 14, backgroundColor: '#161110',
          alignItems: 'center', justifyContent: 'center'},
  stagePlaceholder: {color: '#6f5f54', fontSize: 22},
  cueArea: {minHeight: 132, justifyContent: 'center', paddingVertical: 16},
  cueLabel: {color: '#ff7a45', fontSize: 14, letterSpacing: 3, marginBottom: 8},
  cueText: {color: '#f2e9e1', fontSize: 36, lineHeight: 46, fontWeight: '500'},
  cueIdle: {color: '#6f5f54', fontSize: 22, fontStyle: 'italic'},
  controls: {flexDirection: 'row', alignItems: 'center', marginTop: 20},
  stat: {marginLeft: 'auto', alignItems: 'flex-end'},
  statLabel: {color: '#6f5f54', fontSize: 12, letterSpacing: 3},
  statValue: {color: '#f2e9e1', fontSize: 20, marginTop: 4},
  statNote: {color: '#6f5f54', fontSize: 14, marginTop: 2},
});
