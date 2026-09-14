import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {LayoutChangeEvent} from 'react-native';
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';
import {Video} from '@amazon-devices/react-native-w3cmedia';
import type {HTMLVideoElement} from '@amazon-devices/react-native-w3cmedia';

import {Timeline} from './components/Timeline';
import {Toggle} from './components/Toggle';
import {cueAudioUri, filmUri} from './player/assets';
import {Speaker} from './player/speech';
import {parseTrack, totalSpokenSeconds, type Cue, type Density} from './player/track';
import {useDescriptions} from './player/useDescriptions';
import describedTrack from './data/description.json';

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
  // The track as the backend wrote it, with each cue's audio turned into a URL
  // the device can open. Resolution happens once, here, so nothing downstream
  // has to know that a cue's `audio` started life as a filename.
  const track = useMemo(() => {
    const parsed = parseTrack(describedTrack);
    return {
      ...parsed,
      cues: parsed.cues.map((c) => ({...c, audio: cueAudioUri(c.audio)})),
    };
  }, []);

  const film = useMemo(() => filmUri(), []);

  const [density, setDensity] = useState<Density>('full');
  const [enabled, setEnabled] = useState(true);
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [stage, setStage] = useState({width: 0, height: 0});
  const [source, setSource] = useState<string | undefined>(undefined);
  const [failure, setFailure] = useState<string | null>(null);

  const speaker = useRef<Speaker | null>(null);
  if (speaker.current === null) {
    speaker.current = new Speaker();
  }

  // Hand the audio player back on the way out. A device has a small number of
  // media sessions and the film is holding one of them, so a description player
  // that is never deinitialised is one the next app may not get.
  useEffect(() => () => speaker.current?.release(), []);

  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  // Read through a ref rather than closing over `enabled`, because the
  // scheduler is rebuilt whenever these callbacks change identity and a rebuild
  // forgets which cues have already fired. Toggling description off and on
  // again should not make the film describe itself twice.
  const speak = useCallback((cue: Cue) => {
    if (enabledRef.current) speaker.current?.speak(cue);
  }, []);
  const stop = useCallback(() => speaker.current?.stop(), []);

  const {cues, speaking, spokenCount, onTimeUpdate} = useDescriptions(
    track, density, speak, stop,
  );

  const videoRef = useRef<HTMLVideoElement | null>(null);

  /**
   * The only clock in the app.
   *
   * Vega fires `timeupdate` about four times a second, which is coarse against
   * a gap of a second and a half. Every decision that follows from that is the
   * scheduler's, not this function's: all it does is report the time and
   * whether the film is still moving.
   */
  const tick = useCallback(() => {
    const el = videoRef.current;
    if (!el) return;
    const t = el.currentTime ?? 0;
    setTime(t);
    onTimeUpdate(t, !el.paused);
  }, [onTimeUpdate]);

  // Pause is reported through the same path rather than stopping the speaker
  // directly. The scheduler decides what happens to a cue that was mid-sentence
  // when the viewer hit pause, and it only gets to decide if it is told.
  const handlePause = useCallback(() => {
    setPlaying(false);
    const el = videoRef.current;
    onTimeUpdate(el?.currentTime ?? 0, false);
  }, [onTimeUpdate]);

  const handlePlay = useCallback(() => {
    setFailure(null);
    setPlaying(true);
  }, []);

  /**
   * Attach the film only once the player has a surface to draw on.
   *
   * Passing `src` as a prop looks right and quietly breaks playback. The player
   * applies it during initialisation, which happens before the native video
   * surface exists, so the GStreamer pipeline is built with no video sink
   * attached and the decoder then fails to attach as a writer to a buffer queue
   * that was never created. The surface arrives a moment later and the log says
   * `pipeline already created`, which is the whole story in three words.
   *
   * So the component mounts with no source, and the film is attached one beat
   * after the player reports itself ready, by which time the surface has been
   * registered. The delay is the only part of this that is not principled;
   * there is no public callback for surface attachment to wait on.
   */
  const handlePlayerReady = useCallback(() => {
    setTimeout(() => setSource(film), 250);
  }, [film]);

  const handleMetadata = useCallback(() => {
    const el = videoRef.current;
    if (el && isFinite(el.duration)) setDuration(el.duration);
    // Playback is started here rather than with `autoplay`, because there is
    // nothing to autoplay at the point the player would act on it.
    try {
      el?.play();
    } catch {
      setFailure('The film could not be played.');
    }
  }, []);

  const handleEnded = useCallback(() => {
    setPlaying(false);
    onTimeUpdate(videoRef.current?.currentTime ?? 0, false);
  }, [onTimeUpdate]);

  const handleError = useCallback(() => {
    setPlaying(false);
    setFailure('The film could not be played.');
  }, []);

  /**
   * Hand the player the size of the box it is sitting in, in pixels.
   *
   * `Video` renders a fixed `width`/`height` View and ignores `style`, so
   * without these it lays out at NaN by NaN, the surface underneath it is
   * never created, and the only symptom is a GStreamer line in the device log
   * saying the overlay handle is null. Measuring the stage keeps the layout
   * declarative while still giving the player the two numbers it insists on.
   */
  const measureStage = useCallback((e: LayoutChangeEvent) => {
    const {width, height} = e.nativeEvent.layout;
    setStage({width: Math.round(width), height: Math.round(height)});
  }, []);

  const spoken = totalSpokenSeconds(cues);
  const timelineLength = duration || track.cues.at(-1)?.end || 0;

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title}>Aloud</Text>
        <Text style={styles.strap}>
          A television that describes itself, in the gaps between dialogue.
        </Text>
      </View>

      <View style={styles.stage} testID="stage" onLayout={measureStage}>
        {stage.width > 0 && stage.height > 0 ? (
          <Video
            ref={(r: unknown) => {
              videoRef.current = r as HTMLVideoElement | null;
            }}
            width={stage.width}
            height={stage.height}
            src={source}
            scalingmode="fit"
            onComponentDidMount={handlePlayerReady}
            onTimeUpdate={tick}
            onPlay={handlePlay}
            onPause={handlePause}
            onEnded={handleEnded}
            onLoadedMetadata={handleMetadata}
            onError={handleError}
          />
        ) : null}
        {failure ? <Text style={styles.stageNote}>{failure}</Text> : null}
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
        duration={timelineLength}
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
            {playing ? `${time.toFixed(1)}s · ` : 'paused · '}
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
          alignItems: 'center', justifyContent: 'center', overflow: 'hidden'},
  stageNote: {color: '#6f5f54', fontSize: 22},
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
