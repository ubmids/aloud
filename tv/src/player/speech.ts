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
    } catch {
      // A device without a spare audio player must still play the film. The
      // description is the thing that degrades, never the content.
      this.player = null;
    }
  }

  get available(): boolean {
    return this.player !== null;
  }

  speak(cue: Cue): void {
    if (!this.player || !cue.audio) return;
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
    this.player = null;
  }
}
