import {
  AudioContentType,
  AudioPlayer,
  AudioUsageType,
} from '@amazon-devices/react-native-w3cmedia';

import type {Cue} from './track';

/**
 * Speaking a cue over the film.
 *
 * The description is a second audio stream, not a replacement for the first, so
 * it gets its own player rather than interrupting the film's. The film keeps
 * playing underneath, which is the point: a listener who loses the room tone
 * every time the describer speaks has lost more than they gained.
 *
 * The audio is classified rather than played anonymously. Vega is told this is
 * speech for accessibility, which is what lets the platform treat it correctly
 * against the film and against anything else making noise. Playing it as
 * generic media would leave that decision to luck.
 */
export class Speaker {
  private player: AudioPlayer | null = null;
  private current: Cue | null = null;
  private ready = false;

  constructor() {
    try {
      // Vega has a usage type specifically for accessibility prompts, which is
      // exactly what this is. Classifying it as generic media would put the
      // description in the same category as the film it is describing and leave
      // the platform no way to tell them apart.
      this.player = new AudioPlayer(
        AudioContentType.CONTENT_TYPE_SPEECH,
        AudioUsageType.USAGE_ACCESSIBILITY,
      );
      // The player does nothing at all until this resolves, and it fails
      // silently rather than throwing if you skip it: `src` is accepted, `play`
      // returns, and no sound is produced. Initialisation happens once at
      // startup, long before the first gap, so a cue arriving before the player
      // is ready is dropped rather than queued. A description that turns up late
      // is exactly the thing this system exists to prevent.
      this.player
        .initialize()
        .then(() => {
          this.ready = true;
        })
        .catch(() => {
          this.player = null;
        });
    } catch {
      // A device without a spare audio player must still play the film. The
      // description is the thing that degrades, never the content.
      this.player = null;
    }
  }

  get available(): boolean {
    return this.player !== null && this.ready;
  }

  speak(cue: Cue): void {
    if (!this.player || !this.ready || !cue.audio) return;
    this.current = cue;
    try {
      this.player.src = cue.audio;
      this.player.play();
    } catch {
      this.current = null;
    }
  }

  /**
   * Stop immediately, without a fade.
   *
   * Called when the viewer pauses or seeks, and when a cue's window closes. A
   * fade sounds nicer and is wrong here: the window closing means dialogue is
   * about to start, and the whole purpose is to not be talking when it does.
   */
  stop(): void {
    this.current = null;
    try {
      this.player?.pause();
    } catch {
      // Nothing to do. Failing to stop a sound must not take the app down.
    }
  }

  get speaking(): Cue | null {
    return this.current;
  }

  release(): void {
    this.stop();
    this.ready = false;
    this.player?.deinitialize().catch(() => {});
    this.player = null;
  }
}
