import {useEffect, useState} from 'react';
import {AccessibilityInfo} from 'react-native';

import UI from './data/ui.json';

/**
 * The menu's own voice, for everything that is not a title.
 *
 * A viewer who cannot see the screen has to hear where the remote is. The
 * titles on the shelf were always read out; the settings under them and the
 * controls under the film were silent, so pressing down from the shelf put a
 * viewer on "Voice level" with nothing to say so. Every setting now has one
 * short clip per value, in the same voice as the descriptions, played when it
 * takes focus and again with its new value when select changes it.
 *
 * The words live in `data/ui.json`, which is also what `python3 -m
 * aloud.menu_voice` reads to synthesise the clips into `assets/ui/`, so the
 * clip and the table cannot disagree about what a key says.
 */
export type UiClip = keyof typeof UI;

export const UI_WORDS: Record<UiClip, string> = UI;

/** Where a menu clip lives once the app is packaged (see player/assets.ts). */
export function uiUri(key: UiClip): string {
  return `/pkg/assets/ui/${key}.m4a`;
}

/**
 * Whether VoiceView is running. When it is, the app's own voice stays quiet
 * and VoiceView reads each control's label: two voices reading one menu is
 * worse than either.
 */
export function useScreenReader(): boolean {
  const [on, setOn] = useState(false);
  useEffect(() => {
    let live = true;
    AccessibilityInfo.isScreenReaderEnabled?.()
      .then((v) => live && setOn(!!v))
      .catch(() => {});
    const sub = AccessibilityInfo.addEventListener?.(
      'screenReaderChanged', (v: boolean) => setOn(!!v));
    return () => {
      live = false;
      sub?.remove?.();
    };
  }, []);
  return on;
}
