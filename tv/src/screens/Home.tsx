import React, {useCallback, useRef, useState} from 'react';
import {Image, StyleSheet, Text, View} from 'react-native';
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';

import {announcement, describedSummary, type Film} from '../film';
import {FilmTile} from '../components/FilmTile';
import {GapMark} from '../components/GapMark';
import {Toggle} from '../components/Toggle';
import {clock} from '../format';
import {provenance} from '../provenance';
import {uiUri, useScreenReader} from '../menuVoice';
import {announceUri} from '../player/assets';
import type {Speaker} from '../player/speech';
import {LEVELS, nextLevel, type Settings} from '../settings';
import {font, line, palette, safe, size, u} from '../theme';

/**
 * The shelf.
 *
 * Built for the person the whole app is for: someone holding a remote who
 * may not be able to see the screen. Three things follow.
 *
 * Every move is spoken. When a title takes focus the app plays its name,
 * genre, year, length and how many descriptions it carries, and when a
 * setting takes focus or changes it says the setting and its value, in the
 * same voice that will describe the film, so the shelf and the film are one experience
 * rather than a menu in one voice and a film in another. If VoiceView is
 * running the app stays quiet and lets the screen reader read the same words
 * from the tile's label, because two voices reading one menu is worse than
 * either.
 *
 * Every title says what it is and how it was described before it is played.
 * The shelf names the model that wrote the descriptions and the voice that
 * reads them, in words rather than model IDs, and offers the film's first
 * description as a taste of what it will sound like. A viewer is owed that,
 * and so is anyone deciding whether to trust a track no human wrote.
 *
 * Nothing needs more than left, right, down and select. The row of films is
 * one focus group and the settings are another, and the settings chosen here
 * carry into the player.
 */
export const Home = ({
  films, settings, onSettings, onPlay, speaker, initial,
}: {
  films: Film[];
  settings: Settings;
  onSettings: (s: Settings) => void;
  onPlay: (f: Film) => void;
  speaker: Speaker;
  /** The title to come back to, so Back from a film lands where it left. */
  initial?: string;
}) => {
  const [focused, setFocused] = useState<Film>(
    films.find((f) => f.id === initial) ?? films[0],
  );
  const screenReader = useScreenReader();

  // Speak whatever has focus. Each press cuts off the last announcement: the
  // newest focus is the only one the viewer still cares about, and finishing
  // an old sentence would put the voice a press behind the remote.
  const settingsRef = useRef(settings);
  settingsRef.current = settings;
  const say = useCallback((uri: string, always = false) => {
    if ((!settingsRef.current.speakMenus && !always) || screenReader) return;
    speaker.stop();
    speaker.setVolume(LEVELS[settingsRef.current.level].voice);
    speaker.play(uri);
  }, [speaker, screenReader]);
  // Turning the menu voice off is the one change that would otherwise go
  // unconfirmed, so that setting always answers.
  const sayAlways = useCallback((uri: string) => say(uri, true), [say]);
  const announce = useCallback((f: Film) => say(announceUri(f.id)), [say]);

  const onFocus = useCallback((f: Film) => {
    setFocused(f);
    announce(f);
  }, [announce]);

  // A taste of the track: its first description that is about the picture
  // rather than a title card.
  const taste = focused.track.cues.find((c) => !/^On screen:/.test(c.text));

  return (
    <View style={styles.screen}>
      {/* The picture bleeds off the top right with a hard edge; the words sit
          on solid ground beside it, never on it, so their contrast does not
          depend on which frame the poster happens to be. */}
      <Image source={focused.poster} style={styles.backdrop} resizeMode="cover" />
      <Text style={styles.credit} numberOfLines={1}>
        {focused.credit}  ·  {focused.licence.split(',')[0]}
      </Text>
      {taste ? (
        <View style={styles.taste}>
          <Text style={styles.tasteLabel}>{`First description, at ${clock(taste.start)}`}</Text>
          <Text style={styles.tasteText} numberOfLines={2}>{taste.text}</Text>
        </View>
      ) : null}

      <View style={styles.content}>
      <View style={styles.header}>
        <GapMark height={34} />
        <Text style={styles.wordmark} accessibilityRole="header">aloud</Text>
      </View>

      <View style={styles.details}>
        <Text style={styles.meta}>
          {focused.genre}, {focused.year}, {focused.minutes} minute{focused.minutes === 1 ? '' : 's'}
        </Text>
        <Text style={styles.filmTitle} numberOfLines={1}>{focused.title}</Text>
        <Text style={styles.synopsis} numberOfLines={3}>{focused.synopsis}</Text>
        <View style={styles.describedRow}>
          <GapMark height={24} />
          <Text style={styles.described}>{describedSummary(focused)}</Text>
        </View>
        <Text style={styles.provenance}>
          {provenance(focused.describer, focused.voice)}
        </Text>
      </View>

      <Text style={styles.rowLabel}>Described films</Text>
      <TVFocusGuideView style={styles.row} autoFocus>
        {films.map((f, i) => (
          <FilmTile
            key={f.id}
            film={f}
            label={announcement(f)}
            onFocus={() => onFocus(f)}
            onPress={() => onPlay(f)}
            hasTVPreferredFocus={initial ? f.id === initial : i === 0}
            testID={`tile-${f.id}`}
          />
        ))}
      </TVFocusGuideView>

      <TVFocusGuideView style={styles.settings} autoFocus>
        <Toggle
          label="Narration"
          value={settings.narration ? 'On' : 'Off'}
          help={settings.narration
            ? 'Films start with their descriptions playing.'
            : 'Films start with their own sound only.'}
          checked={settings.narration}
          onPress={() => onSettings({...settings, narration: !settings.narration})}
          testID="home-narration"
          spoken={uiUri(settings.narration ? 'narration-on' : 'narration-off')}
          speak={say}
          width={u(408)}
        />
        <Toggle
          label="Voice level"
          value={LEVELS[settings.level].label}
          help={LEVELS[settings.level].help}
          onPress={() => onSettings({...settings, level: nextLevel(settings.level)})}
          testID="home-level"
          spoken={uiUri(`level-${settings.level}`)}
          speak={say}
          width={u(408)}
        />
        <Toggle
          label="How much is said"
          value={settings.density === 'full' ? 'Everything' : 'Only what changed most'}
          help={settings.density === 'full'
            ? 'Every description there was room for.'
            : 'Half as much talking, kept for the biggest changes.'}
          onPress={() => onSettings({...settings,
            density: settings.density === 'full' ? 'sparse' : 'full'})}
          testID="home-density"
          spoken={uiUri(settings.density === 'full' ? 'density-full' : 'density-sparse')}
          speak={say}
          width={u(408)}
        />
        <Toggle
          label="Read the menu aloud"
          value={settings.speakMenus ? 'On' : 'Off'}
          help={screenReader
            ? 'VoiceView is on, so it reads the menu instead.'
            : 'Each title is read out as you move to it.'}
          checked={settings.speakMenus}
          onPress={() => onSettings({...settings, speakMenus: !settings.speakMenus})}
          testID="home-speak-menus"
          spoken={uiUri(settings.speakMenus ? 'menus-on' : 'menus-off')}
          speak={sayAlways}
          width={u(408)}
        />
      </TVFocusGuideView>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  screen: {flex: 1, backgroundColor: palette.ground},
  // The Fire TV safe area: 5% of the screen on every side.
  content: {flex: 1, paddingHorizontal: safe.x, paddingVertical: safe.y},
  backdrop: {position: 'absolute', right: 0, top: 0, width: u(920), height: u(380)},
  credit: {...font.regular, position: 'absolute', right: safe.x, top: u(392),
           width: u(920) - safe.x, color: palette.inkMuted, fontSize: size.label,
           lineHeight: line.label},
  taste: {position: 'absolute', right: safe.x, top: u(432), width: u(920) - safe.x},
  tasteLabel: {...font.semibold, color: palette.inkMuted, fontSize: size.label,
               lineHeight: line.label},
  tasteText: {...font.regular, color: palette.inkSoft, fontSize: size.label,
              lineHeight: line.label},

  header: {flexDirection: 'row', alignItems: 'center', height: u(52)},
  wordmark: {...font.heavy, color: palette.ink, fontSize: u(44), lineHeight: u(52),
             marginLeft: u(16)},

  details: {width: u(820), marginTop: u(20)},
  meta: {...font.regular, color: palette.inkSoft, fontSize: size.body, lineHeight: line.body},
  filmTitle: {...font.heavy, color: palette.ink, fontSize: size.display,
              lineHeight: line.display},
  synopsis: {...font.regular, color: palette.inkSoft, fontSize: size.body,
             lineHeight: line.body, marginTop: u(6)},
  describedRow: {flexDirection: 'row', alignItems: 'center', marginTop: u(14)},
  described: {...font.semibold, color: palette.ink, fontSize: size.lead,
              lineHeight: line.lead, marginLeft: u(14)},
  provenance: {...font.regular, color: palette.inkMuted, fontSize: size.label,
               lineHeight: line.label, marginTop: u(2)},

  rowLabel: {...font.semibold, color: palette.inkSoft, fontSize: size.label,
             lineHeight: line.label, marginTop: u(12), marginBottom: u(16)},
  row: {flexDirection: 'row'},
  settings: {flexDirection: 'row', marginTop: u(22)},
});
