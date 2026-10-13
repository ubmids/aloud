import React, {useCallback, useRef, useState} from 'react';
import {Image, StyleSheet, Text, View} from 'react-native';
import {TVFocusGuideView} from '@amazon-devices/react-native-kepler';

import {announcement, describedSummary, type Film} from '../film';
import {FilmTile} from '../components/FilmTile';
import {Toggle} from '../components/Toggle';
import {uiUri, useScreenReader} from '../menuVoice';
import {announceUri} from '../player/assets';
import type {Speaker} from '../player/speech';
import {LEVELS, nextLevel, type Settings} from '../settings';
import {palette, size, u} from '../theme';

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
 * The panel names the model that wrote the descriptions and the voice that
 * reads them. A viewer is owed that, and so is anyone deciding whether to
 * trust a track no human wrote.
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

  return (
    <View style={styles.screen}>
      <View style={styles.header}>
        <Text style={styles.wordmark} accessibilityRole="header">aloud</Text>
        <View style={styles.rule} />
        <Text style={styles.strap}>
          Films that describe themselves, in the gaps between dialogue.
        </Text>
      </View>

      <View style={styles.feature}>
        <Image source={focused.poster} style={styles.backdrop} resizeMode="cover" />
        <View style={styles.scrim} />
        <View style={styles.details}>
          <Text style={styles.eyebrow}>
            {focused.genre.toUpperCase()}  ·  {focused.year}  ·  {focused.minutes} MIN
          </Text>
          <Text style={styles.filmTitle}>{focused.title}</Text>
          <Text style={styles.synopsis}>{focused.synopsis}</Text>
          <View style={styles.describedRow}>
            <View style={styles.dot} />
            <Text style={styles.described}>{describedSummary(focused)}</Text>
          </View>
          <Text style={styles.provenance}>
            Described ahead of time by {focused.describer || 'the Aloud pipeline'}
            {focused.voice ? `, read by ${focused.voice}` : ''}. Every
            description sits in a measured silence.
          </Text>
          <Text style={styles.credit}>{focused.credit}  ·  {focused.licence}</Text>
        </View>
      </View>

      <Text style={styles.rowLabel}>DESCRIBED FILMS</Text>
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
        />
        <Toggle
          label="Voice level"
          value={LEVELS[settings.level].label}
          help={LEVELS[settings.level].help}
          onPress={() => onSettings({...settings, level: nextLevel(settings.level)})}
          testID="home-level"
          spoken={uiUri(`level-${settings.level}`)}
          speak={say}
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
        />
      </TVFocusGuideView>
    </View>
  );
};

const styles = StyleSheet.create({
  // Television safe area, as in the player.
  screen: {flex: 1, backgroundColor: palette.ground, paddingHorizontal: u(64),
           paddingVertical: u(44)},
  header: {flexDirection: 'row', alignItems: 'center', marginBottom: u(22)},
  wordmark: {color: palette.ink, fontSize: size.wordmark, fontWeight: '700',
             letterSpacing: u(-1)},
  rule: {width: u(2), height: u(26), backgroundColor: palette.edge,
         marginHorizontal: u(20)},
  strap: {color: palette.inkMuted, fontSize: size.strap, flexShrink: 1},

  feature: {height: u(470), borderRadius: u(16), overflow: 'hidden',
            backgroundColor: palette.recess, borderWidth: u(2),
            borderColor: palette.edge, justifyContent: 'center'},
  backdrop: {position: 'absolute', right: 0, top: 0, bottom: 0, width: '62%',
             height: '100%'},
  // The words sit on solid ground, never on the picture, so their contrast
  // does not depend on which frame the poster happens to be.
  scrim: {position: 'absolute', left: 0, top: 0, bottom: 0, width: '46%',
          backgroundColor: palette.recess},
  details: {width: '44%', paddingHorizontal: u(44)},
  eyebrow: {color: palette.inkMuted, fontSize: size.eyebrow, letterSpacing: u(4)},
  filmTitle: {color: palette.ink, fontSize: u(60), fontWeight: '700',
              marginTop: u(10), letterSpacing: u(-1)},
  synopsis: {color: palette.inkSoft, fontSize: size.body, lineHeight: u(30),
             marginTop: u(12)},
  describedRow: {flexDirection: 'row', alignItems: 'center', marginTop: u(20)},
  dot: {width: u(14), height: u(14), borderRadius: u(7),
        backgroundColor: palette.voice, marginRight: u(12)},
  described: {color: palette.ink, fontSize: size.lead, fontWeight: '600'},
  provenance: {color: palette.inkSoft, fontSize: size.eyebrow, lineHeight: u(25),
               marginTop: u(10)},
  credit: {color: palette.inkMuted, fontSize: size.eyebrow, marginTop: u(14)},

  rowLabel: {color: palette.inkMuted, fontSize: size.eyebrow, letterSpacing: u(4),
             marginTop: u(26), marginBottom: u(12)},
  row: {flexDirection: 'row'},
  settings: {flexDirection: 'row', marginTop: u(26)},
});
