import React, {useCallback, useEffect, useMemo, useRef, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {LayoutChangeEvent} from 'react-native';
import {
  TVFocusGuideView,
  useComponentInstance,
  useTVEventHandler,
} from '@amazon-devices/react-native-kepler';
import type {HWEvent} from '@amazon-devices/react-native-kepler';
import {Video} from '@amazon-devices/react-native-w3cmedia';
import type {HTMLVideoElement} from '@amazon-devices/react-native-w3cmedia';

import type {Film} from '../film';
import {Timeline} from '../components/Timeline';
import {Toggle} from '../components/Toggle';
import {Voice} from '../components/Voice';
import {secs} from '../format';
import {uiUri, useScreenReader} from '../menuVoice';
import {remember, SAID_MORE, shouldSayMore} from '../player/adapt';
import {cueAudioUri, filmUri} from '../player/assets';
import {lastDescribed, nextCueFrom} from '../player/schedule.js';
import {Speaker} from '../player/speech';
import {totalSpokenSeconds, type Cue} from '../player/track';
import {useDescriptions} from '../player/useDescriptions';
import {filmVolume, LEVELS, nextLevel, type Settings} from '../settings';
import {palette, size, u} from '../theme';

/** How far the remote's skip buttons move the film. */
const SKIP_S = 10;

/** In full screen, how long the controls stay up after the last key press. */
export const CHROME_MS = 5000;

/**
 * The player: one film, described.
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
 *
 * That layout is for showing what description is. For watching a film it is
 * a dashboard, so "Picture: Full screen" turns it into a television player:
 * the film fills the screen, the description being spoken shows as a caption
 * over it, and the controls fade after a few seconds and come back on any
 * key. Nothing about what is heard changes.
 */
export const Player = ({
  film: title, settings, onSettings, speaker: shared,
}: {
  film: Film;
  settings: Settings;
  onSettings: (s: Settings) => void;
  /** The app's one description voice, shared with the shelf so the device is
   *  never asked for a second accessibility audio session. */
  speaker: Speaker;
}) => {
  // The track as the backend wrote it, with each cue's audio turned into a URL
  // the device can open. Resolution happens once, here, so nothing downstream
  // has to know that a cue's `audio` started life as a filename.
  const track = useMemo(() => ({
    ...title.track,
    cues: title.track.cues.map((c) => ({...c, audio: cueAudioUri(title.id, c.audio)})),
  }), [title]);

  const film = useMemo(() => filmUri(title.id), [title]);

  const density = settings.density;
  const densityRef = useRef(density);
  densityRef.current = density;
  // Menu presses, by wall clock, and whether the last density change was the
  // player's own answer to them rather than the viewer's (see adapt.ts).
  const asks = useRef<number[]>([]);
  const [saidMore, setSaidMore] = useState(false);
  const enabled = settings.narration;
  const [time, setTime] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [stage, setStage] = useState({width: 0, height: 0});
  const [source, setSource] = useState<string | undefined>(undefined);
  const [failure, setFailure] = useState<string | null>(null);

  const speaker = useRef<Speaker>(shared);
  speaker.current = shared;

  // The controls say their name and value when they take focus and when
  // select changes them, in the description voice, unless VoiceView is
  // reading them or the viewer turned the menu voice off on the shelf.
  const screenReader = useScreenReader();
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const onSettingsRef = useRef(onSettings);
  onSettingsRef.current = onSettings;
  const say = useCallback((uri: string) => {
    if (!settingsRef.current.speakMenus || screenReader) return;
    speaker.current.stop();
    speaker.current.setVolume(LEVELS[settingsRef.current.level].voice);
    speaker.current.play(uri);
  }, [screenReader]);

  const full = settings.picture === 'full';
  const [chrome, setChrome] = useState(true);
  const chromeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wake = useCallback(() => {
    setChrome(true);
    if (chromeTimer.current) clearTimeout(chromeTimer.current);
    chromeTimer.current = setTimeout(() => setChrome(false), CHROME_MS);
  }, []);
  useEffect(() => {
    if (full) {
      wake();
    } else {
      if (chromeTimer.current) clearTimeout(chromeTimer.current);
      setChrome(true);
    }
    return () => {
      if (chromeTimer.current) clearTimeout(chromeTimer.current);
    };
  }, [full, wake]);

  // Leaving the film must not leave a sentence hanging over the shelf.
  useEffect(() => () => speaker.current.stop(), []);

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
  const component = useComponentInstance();

  /**
   * "What did I miss?", on the Menu button.
   *
   * The film pauses and the last description is said again, then the film
   * carries on by itself. It works with narration off too, which makes it a
   * second way to watch: a sighted viewer on the same sofa hears the film as
   * it was made, and the viewer who needs to know what is on screen asks, at
   * the moment they need to, with one button. The film is paused first so the
   * repeat can never land on a line of dialogue, the same promise every other
   * description keeps.
   */
  const [again, setAgain] = useState<Cue | null>(null);
  const againTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const clearAgain = useCallback(() => {
    if (againTimer.current) clearTimeout(againTimer.current);
    againTimer.current = null;
    setAgain(null);
  }, []);
  useEffect(() => () => {
    if (againTimer.current) clearTimeout(againTimer.current);
  }, []);
  const sayAgain = useCallback(() => {
    const el = videoRef.current;
    const t = el?.currentTime ?? 0;
    const cue = lastDescribed(track.cues, t) as Cue | null;
    if (!el || !cue) return;
    // Tell the scheduler about the pause now rather than when the pause event
    // arrives, so it lets go of anything mid-sentence before the repeat starts
    // and has nothing left to stop when the event does arrive.
    const wasPlaying = !el.paused;
    onTimeUpdate(t, false);
    el.pause();
    speaker.current.stop();
    speaker.current.speak(cue);
    clearAgain();
    setAgain(cue);
    asks.current = remember(asks.current, Date.now());
    if (shouldSayMore(asks.current, densityRef.current)) {
      asks.current = [];
      onSettingsRef.current({...settingsRef.current, density: 'full'});
      setSaidMore(true);
    }
    againTimer.current = setTimeout(() => {
      againTimer.current = null;
      setAgain(null);
      // A film the viewer had paused stays paused; asking a question is not
      // asking for the film to start.
      if (!wasPlaying) return;
      try {
        el.play();
      } catch {
        // The viewer can still press play.
      }
    }, (cue.end - cue.start + 0.5) * 1000);
  }, [track, onTimeUpdate, clearAgain]);

  // The voice level is two numbers: how loud the describer is, and how far
  // the film dips while it speaks. The dip happens only while a description is
  // playing, and a description only ever plays inside a gap in the dialogue,
  // so no line of dialogue is ever turned down.
  useEffect(() => {
    speaker.current.setVolume(LEVELS[settings.level].voice);
  }, [settings.level]);
  useEffect(() => {
    const el = videoRef.current;
    if (!el) return;
    try {
      el.volume = filmVolume(settings.level, speaking !== null, enabled);
    } catch {
      // A player that will not take a volume plays the film at full scale,
      // which is the film as it was made.
    }
  }, [speaking, settings.level, enabled]);

  /**
   * The remote, beyond focus. Play/pause and the skip buttons drive the film
   * directly, and every one of them goes through the scheduler's clock, so a
   * skip backwards re-arms the descriptions it passes and a skip forwards
   * drops the ones it jumps over, exactly as a scrub does.
   */
  const remote = useCallback((e: HWEvent) => {
    const el = videoRef.current;
    // Ignore key-down, so one press is one action. A build that reports no
    // key state at all still works (see friction log entry 16).
    if (e.eventKeyAction === 0) return;
    // Any key brings the full-screen controls back.
    if (settingsRef.current.picture === 'full') wake();
    if (!el) return;
    const seek = (delta: number) => {
      const to = Math.max(0, Math.min((el.duration || Infinity) - 1,
                                      (el.currentTime ?? 0) + delta));
      el.currentTime = to;
      onTimeUpdate(to, !el.paused);
    };
    switch (e.eventType) {
      case 'menu':
      case 'info':
        sayAgain();
        break;
      case 'playpause':
      case 'pause':
        if (el.paused) el.play(); else el.pause();
        break;
      case 'rewind':
      case 'skip_backward':
        seek(-SKIP_S);
        break;
      case 'fastforward':
      case 'skip_forward':
        seek(SKIP_S);
        break;
    }
  }, [onTimeUpdate, sayAgain, wake]);
  useTVEventHandler(remote);

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
    // Pressing play during a repeat is the viewer saying they have heard
    // enough; the film is already moving, so there is nothing to resume.
    clearAgain();
  }, [clearAgain]);

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
    // Hand Vega's media controls to this player, so the voice remote's
    // "Alexa, pause" and "Alexa, rewind" reach the film. The w3cmedia player
    // answers those commands itself once it has focus; the descriptions follow
    // because every transport change comes back through `timeupdate`.
    try {
      void (el as any)?.setMediaControlFocus?.(component);
    } catch {
      // Without voice transport the remote still works.
    }
    // Playback is started here rather than with `autoplay`, because there is
    // nothing to autoplay at the point the player would act on it.
    try {
      el?.play();
    } catch {
      setFailure('The film could not be played.');
    }
  }, [component]);

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
  const caption = speaking ?? again;

  return (
    <View style={full ? styles.screenFull : styles.screen}>
      {full ? null : <View style={styles.header}>
        <Text style={styles.title} accessibilityRole="header">
          aloud
        </Text>
        <View style={styles.rule} />
        <Text style={styles.strap} numberOfLines={1}>
          {title.title}
          <Text style={styles.strapSoft}>
            {'  '}Menu says the last description again.
          </Text>
        </Text>
        <Text
          style={styles.tally}
          numberOfLines={1}
          accessibilityLabel={
            `This film: ${cues.length} descriptions, ${secs(spoken)} of speech ` +
            `in total. ${spokenCount} spoken so far, each inside a measured gap ` +
            'in the dialogue.'
          }>
          {cues.length} descriptions  ·  {spokenCount} spoken so far, each inside a measured gap
        </Text>
        {/* The state is in the word as well as the dot. A viewer who cannot
            separate a lit dot from an unlit one still reads "PAUSED". */}
        <View style={styles.status}>
          <View style={[styles.statusDot, playing && styles.statusDotLive]} />
          <Text style={styles.statusText}>{playing ? 'PLAYING' : 'PAUSED'}</Text>
        </View>
      </View>}

      <View style={full ? styles.mainFull : styles.main}>
        <View
          style={full ? styles.stageFull : styles.stage}
          testID="stage"
          onLayout={measureStage}
          accessible
          accessibilityLabel={`The film: ${title.title}.`}>
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
          {full && caption && (enabled || again !== null) ? (
            <View style={styles.caption} testID="caption">
              <Text style={styles.captionText}>{caption.text}</Text>
            </View>
          ) : null}
        </View>

        {full ? null : (
          <Voice speaking={caption} next={next} enabled={enabled || again !== null}
                 time={time} />
        )}
      </View>

      {full ? null : (
        <Timeline
          duration={timelineLength}
          cues={cues}
          current={time}
          speaking={speaking}
        />
      )}

      <TVFocusGuideView
        style={full ? [styles.controlsFull, {opacity: chrome ? 1 : 0}] : styles.controls}
        testID="controls">
        <Toggle
          label="Narration"
          value={enabled ? 'On' : 'Off'}
          help={
            enabled
              ? 'A voice describes the picture in the silences.'
              : 'The film plays with its own sound only.'
          }
          checked={enabled}
          onPress={() => {
            onSettings({...settings, narration: !enabled});
            stop();
          }}
          hasTVPreferredFocus
          testID="toggle-enabled"
          spoken={uiUri(enabled ? 'narration-on' : 'narration-off')}
          speak={say}
        />
        <Toggle
          label="Voice level"
          value={LEVELS[settings.level].label}
          help={LEVELS[settings.level].help}
          onPress={() => onSettings({...settings, level: nextLevel(settings.level)})}
          testID="toggle-level"
          spoken={uiUri(`level-${settings.level}`)}
          speak={say}
        />
        <Toggle
          label="How much is said"
          value={density === 'full' ? 'Everything' : 'Only what changed most'}
          help={
            density === 'full'
              ? (saidMore ? SAID_MORE : 'Every description there was room for.')
              : 'Half as much talking, kept for the biggest changes.'
          }
          onPress={() => {
            asks.current = [];
            setSaidMore(false);
            onSettings({...settings, density: density === 'full' ? 'sparse' : 'full'});
          }}
          testID="toggle-density"
          spoken={uiUri(density === 'full' ? 'density-full' : 'density-sparse')}
          speak={say}
        />
        <Toggle
          label="Picture"
          value={full ? 'Full screen' : 'With the voice panel'}
          help={full
            ? 'Descriptions show as captions over the film.'
            : 'The film sits beside what is being said.'}
          onPress={() => onSettings({...settings, picture: full ? 'panel' : 'full'})}
          testID="toggle-picture"
          spoken={uiUri(full ? 'picture-full' : 'picture-panel')}
          speak={say}
        />
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
  strap: {color: palette.ink, fontSize: size.strap, flexShrink: 1, fontWeight: '600'},
  strapSoft: {color: palette.inkMuted, fontWeight: '400'},
  tally: {color: palette.inkSoft, fontSize: size.eyebrow, marginLeft: 'auto',
          paddingLeft: u(24)},
  status: {flexDirection: 'row', alignItems: 'center', paddingLeft: u(28)},
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

  // Full screen: no safe-area padding on the picture itself (a set crops the
  // film's edges the same way it crops any film), but the caption and the
  // controls keep to the safe area.
  screenFull: {flex: 1, backgroundColor: '#000000'},
  mainFull: {position: 'absolute', top: 0, left: 0, right: 0, bottom: 0},
  stageFull: {position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
              backgroundColor: '#000000',
              alignItems: 'center', justifyContent: 'center', overflow: 'hidden'},
  caption: {position: 'absolute', left: u(64), bottom: u(190), maxWidth: '62%',
            backgroundColor: 'rgba(0,0,0,0.78)', borderLeftWidth: u(8),
            borderLeftColor: palette.voice, paddingHorizontal: u(24),
            paddingVertical: u(14), borderRadius: u(6)},
  captionText: {color: '#FFFFFF', fontSize: u(34), lineHeight: u(44)},
  controlsFull: {position: 'absolute', left: u(64), right: u(64), bottom: u(44),
                 flexDirection: 'row', alignItems: 'center'},

  controls: {flexDirection: 'row', alignItems: 'center', marginTop: u(22)},
});
