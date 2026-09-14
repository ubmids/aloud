/**
 * Firing descriptions from a video player that only tells you the time.
 *
 * Vega OS gives a React Native app the W3C media surface and nothing below it:
 * `currentTime`, and a `timeupdate` event. There are no frame callbacks, so the
 * app cannot see the picture, and it does not need to. The track was built
 * against the film in advance; all that is left is saying the right thing at the
 * right moment, and refusing to say it at the wrong one.
 *
 * `timeupdate` is the whole difficulty. It fires roughly four times a second,
 * which is coarse next to gaps of a second and a half, so the scheduler is
 * always finding out slightly late. Everything here follows from that:
 *
 *  - A cue is only started if the rest of its gap can still hold it. Arriving
 *    200ms late into a window with 300ms of speech left means the description
 *    runs past the gap and lands on the next line. Better to say nothing.
 *  - A cue is never started late for the same reason, and lateness is measured
 *    against what is left of the window rather than against the cue's start.
 *  - Seeking backwards re-arms cues; seeking forwards past a cue discards it.
 *    A description that fires because the viewer scrubbed backwards over it is
 *    describing a moment that already happened.
 *  - Nothing fires while paused, and rate changes shrink the window, because a
 *    gap at double speed is half as long while the speech is not.
 */

export class DescriptionScheduler {
  /**
   * @param {Array<{start:number,end:number,text:string,duration?:number}>} cues
   * @param {object} opts
   * @param {(cue:object)=>void} opts.onSpeak   start speaking a cue
   * @param {()=>void} [opts.onStop]            stop whatever is speaking
   * @param {number} [opts.seekThreshold]       jump size that counts as a seek
   */
  constructor(cues = [], opts = {}) {
    this.cues = [...cues]
      .map((c, i) => ({ ...c, id: c.id ?? i, duration: c.duration ?? (c.end - c.start) }))
      .sort((a, b) => a.start - b.start);
    this.onSpeak = opts.onSpeak || (() => {});
    this.onStop = opts.onStop || (() => {});
    this.seekThreshold = opts.seekThreshold ?? 1.0;
    this.reset();
  }

  reset() {
    this.fired = new Set();
    this.lastTime = null;
    this.speaking = null;
    this.rate = 1;
  }

  setRate(rate) {
    this.rate = rate > 0 ? rate : 1;
  }

  /** Call from `timeupdate`. `playing` is false while paused or buffering. */
  update(currentTime, playing = true) {
    const t = currentTime;

    if (this.lastTime !== null && Math.abs(t - this.lastTime) > this.seekThreshold) {
      this._onSeek(t);
    }
    this.lastTime = t;

    if (this.speaking && t >= this.speaking.end) {
      this.speaking = null;                       // the window closed
    }
    if (!playing) {
      if (this.speaking) { this.onStop(); this.speaking = null; }
      return null;
    }
    if (this.speaking) return null;               // one voice at a time

    for (const cue of this.cues) {
      if (this.fired.has(cue.id)) continue;
      if (t < cue.start) break;                   // sorted: nothing earlier is due
      if (t >= cue.end) { this.fired.add(cue.id); continue; }   // missed it

      // The rest of the window has to hold the rest of the description. At
      // faster playback the window passes sooner while the speech does not, so
      // the remaining time is discounted by the rate.
      const remaining = (cue.end - t) / this.rate;
      if (remaining < cue.duration) {
        this.fired.add(cue.id);                   // too late to start safely
        continue;
      }

      this.fired.add(cue.id);
      this.speaking = cue;
      this.onSpeak(cue);
      return cue;
    }
    return null;
  }

  _onSeek(t) {
    if (this.speaking) { this.onStop(); this.speaking = null; }
    // Backwards: re-arm anything now in the future, so a rewatch is described.
    // Forwards: discard anything skipped over, because describing it now would
    // describe a moment the viewer has already passed.
    for (const cue of this.cues) {
      if (cue.start >= t) this.fired.delete(cue.id);
      else this.fired.add(cue.id);
    }
  }
}

export default DescriptionScheduler;
