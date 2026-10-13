import React, {useCallback, useEffect, useRef, useState} from 'react';
import {BackHandler} from 'react-native';

import {FILMS, type Film} from './catalogue';
import {Speaker} from './player/speech';
import {Home} from './screens/Home';
import {Player} from './screens/Player';
import {DEFAULTS, type Settings} from './settings';

/**
 * aloud: films that describe themselves.
 *
 * Two screens and one voice. The shelf reads each title aloud as the remote
 * moves across it; select plays it with its descriptions; Back returns to the
 * shelf, on the title that was playing. The same description voice, at the
 * same level, speaks the menu and the film, so a viewer who cannot see the
 * screen gets one continuous experience rather than a menu and then a film.
 *
 * The voice is one `AudioPlayer` for the life of the app, created here and
 * lent to both screens. A device has a small number of media sessions and the
 * film is holding one, so a second description player per screen is a session
 * the next app may not get.
 */
export const App = () => {
  const [settings, setSettings] = useState<Settings>(DEFAULTS);
  const [playing, setPlaying] = useState<Film | null>(null);
  const [lastPlayed, setLastPlayed] = useState<string | undefined>(undefined);

  const speaker = useRef<Speaker | null>(null);
  if (speaker.current === null) {
    speaker.current = new Speaker();
  }
  useEffect(() => () => speaker.current?.release(), []);

  const play = useCallback((f: Film) => {
    speaker.current?.stop();
    setLastPlayed(f.id);
    setPlaying(f);
  }, []);

  // Back from a film goes to the shelf, not out of the app. Back from the
  // shelf is left to the system, which is what a viewer expects of a TV app.
  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (playing === null) return false;
      speaker.current?.stop();
      setPlaying(null);
      return true;
    });
    return () => sub.remove();
  }, [playing]);

  if (playing) {
    return (
      <Player
        key={playing.id}
        film={playing}
        settings={settings}
        onSettings={setSettings}
        speaker={speaker.current}
      />
    );
  }
  return (
    <Home
      films={FILMS}
      settings={settings}
      onSettings={setSettings}
      onPlay={play}
      speaker={speaker.current}
      initial={lastPlayed}
    />
  );
};
