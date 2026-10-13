/**
 * The three things a viewer can change, and what each one actually does.
 *
 * Kept free of React so the rules can be tested without a device, and so the
 * home screen and the player agree about them by importing one file rather
 * than by both being careful.
 */

/** How loud the describer is, as a viewer would say it. */
export type VoiceLevel = 'quiet' | 'normal' | 'loud';

export const VOICE_LEVELS: VoiceLevel[] = ['quiet', 'normal', 'loud'];

/**
 * Voice level is two numbers, not one.
 *
 * Turning the description up on its own does little: the film is already at
 * full scale and the voice cannot go above it. So each level also says how far
 * the film dips while the describer is speaking. Quiet keeps the film almost
 * where it was, which is what a sighted viewer sharing the sofa wants; loud
 * drops it well back, which is what a viewer relying on every word wants. The
 * dip only ever happens inside a gap in the dialogue, because that is the only
 * place a description is ever spoken, so no line of dialogue is ever ducked.
 */
export const LEVELS: Record<VoiceLevel, {voice: number; film: number; label: string; help: string}> = {
  quiet: {voice: 0.65, film: 0.85, label: 'Quiet',
          help: 'The film barely dips when the voice speaks.'},
  normal: {voice: 0.85, film: 0.6, label: 'Normal',
           help: 'The film dips under each description.'},
  loud: {voice: 1.0, film: 0.4, label: 'Loud',
         help: 'The film drops well back so every word is clear.'},
};

export function nextLevel(level: VoiceLevel): VoiceLevel {
  return VOICE_LEVELS[(VOICE_LEVELS.indexOf(level) + 1) % VOICE_LEVELS.length];
}

/** The film's volume right now, given whether the describer is speaking. */
export function filmVolume(level: VoiceLevel, speaking: boolean, narration: boolean): number {
  return narration && speaking ? LEVELS[level].film : 1.0;
}

export type Settings = {
  narration: boolean;
  level: VoiceLevel;
  /** Speak the catalogue as focus moves, in the describer's own voice. */
  speakMenus: boolean;
};

export const DEFAULTS: Settings = {narration: true, level: 'normal', speakMenus: true};
