import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {LayoutChangeEvent} from 'react-native';
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';
import {Video} from '@amazon-devices/react-native-w3cmedia';
import type {HTMLVideoElement} from '@amazon-devices/react-native-w3cmedia';

import {Timeline} from './components/Timeline';
import {Toggle} from './components/Toggle';
import {Voice} from './components/Voice';
import {secs} from './format';
import {cueAudioUri, filmUri} from './player/assets';
import {nextCueFrom} from './player/schedule.js';
import {Speaker} from './player/speech';
import {parseTrack, totalSpokenSeconds, type Cue, type Density} from './player/track';
import {useDescriptions} from './player/useDescriptions';
import {palette, size, u} from './theme';
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
 *
 * The layout follows from that. The film and the voice sit side by side at the
 * top, the same size relationship they have in the experience: the picture is
 * the thing, the voice is beside it and never over it. Underneath, at full
 * width, is the evidence. The controls are last because they are used once.
 * Read top to bottom it is: here is the film, here is what was said, here is
 * where it was said, here is how to change it.
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
  const next = nextCueFrom(cues, time) as Cue | null;

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.title} accessibilityRole="header">
          Aloud
        </Text>
        <View style={styles.rule} />
        <Text style={styles.strap}>
          A television that describes itself, in the gaps between dialogue.
        </Text>
        {/* The state is in the word as well as the dot. A viewer who cannot
            separate a lit dot from an unlit one still reads "PAUSED". */}
        <View style={styles.status}>
          <View style={[styles.statusDot, playing && styles.statusDotLive]} />
          <Text style={styles.statusText}>{playing ? 'PLAYING' : 'PAUSED'}</Text>
        </View>
      </View>

      <View style={styles.main}>
        <View
          style={styles.stage}
          testID="stage"
          onLayout={measureStage}
          accessible
          accessibilityLabel="The film: the Sintel trailer.">
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

        <Voice speaking={speaking} next={next} enabled={enabled} time={time} />
      </View>

      <Timeline
        duration={timelineLength}
        cues={cues}
        current={time}
        speaking={speaking}
      />

      <TVFocusGuideView style={styles.controls}>
        <Toggle
          label="Audio description"
          value={enabled ? 'On' : 'Off'}
          help={
            enabled
              ? 'A voice describes the picture in the silences.'
              : 'The film plays with its own sound only.'
          }
          checked={enabled}
          onPress={() => {
            setEnabled((v) => !v);
            stop();
          }}
          hasTVPreferredFocus
          testID="toggle-enabled"
        />
        <Toggle
          label="How much is said"
          value={density === 'full' ? 'Everything' : 'Only what changed most'}
          help={
            density === 'full'
              ? 'Every description there was room for.'
              : 'Half as much talking, kept for the biggest changes.'
          }
          onPress={() => setDensity((d) => (d === 'full' ? 'sparse' : 'full'))}
          testID="toggle-density"
        />
        <View
          style={styles.evidence}
          accessible
          accessibilityLabel={
            `This film: ${cues.length} descriptions, ${secs(spoken)} of speech ` +
            `in total. ${spokenCount} spoken so far, each one inside a measured ` +
            'silence.'
          }>
          <Text style={styles.evidenceLabel}>THIS FILM</Text>
          <Text style={styles.evidenceValue}>
            {cues.length} descriptions, {secs(spoken)} of speech
          </Text>
          <Text style={styles.evidenceNote}>
            {spokenCount} spoken so far, none of them over a line
          </Text>
        </View>
      </TVFocusGuideView>
    </View>
  );
};

const styles = StyleSheet.create({
  // Padding is the television safe area, not taste. Anything nearer the edge
  // than this is cropped by some sets before anyone sees it.
  screen: {flex: 1, backgroundColor: palette.ground, paddingHorizontal: u(64),
           paddingVertical: u(44)},

  header: {flexDirection: 'row', alignItems: 'center', marginBottom: u(18)},
  title: {color: palette.ink, fontSize: size.wordmark, fontWeight: '700',
          letterSpacing: u(-1)},
  rule: {width: u(2), height: u(26), backgroundColor: palette.edge,
         marginHorizontal: u(20)},
  strap: {color: palette.inkMuted, fontSize: size.strap, flexShrink: 1},
  status: {flexDirection: 'row', alignItems: 'center', marginLeft: 'auto',
           paddingLeft: u(24)},
  statusDot: {width: u(14), height: u(14), borderRadius: u(7), marginRight: u(12),
              borderWidth: u(2), borderColor: palette.inkMuted},
  statusDotLive: {backgroundColor: palette.voice, borderColor: palette.voice},
  statusText: {color: palette.inkSoft, fontSize: size.eyebrow,
               letterSpacing: u(4), fontWeight: '700'},

  main: {flex: 1, flexDirection: 'row', marginBottom: u(24)},
  stage: {flex: 3, borderRadius: u(14), backgroundColor: palette.recess,
          borderWidth: u(2), borderColor: palette.edge, alignItems: 'center',
          justifyContent: 'center', overflow: 'hidden'},
  stageNote: {color: palette.inkMuted, fontSize: size.lead},

  controls: {flexDirection: 'row', alignItems: 'center', marginTop: u(22)},
  evidence: {marginLeft: 'auto', alignItems: 'flex-end'},
  evidenceLabel: {color: palette.inkMuted, fontSize: size.eyebrow,
                  letterSpacing: u(4)},
  evidenceValue: {color: palette.ink, fontSize: size.lead, marginTop: u(8)},
  evidenceNote: {color: palette.inkSoft, fontSize: size.body, marginTop: u(6)},
});
