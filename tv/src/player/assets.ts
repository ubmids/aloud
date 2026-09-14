/**
 * Where the film and the spoken cues actually live once the app is packaged.
 *
 * Everything Aloud plays is bundled, not fetched. A description track is only
 * safe if it was built against the exact file being played: a different cut, a
 * different encode, and every cue start is measured against a timeline that no
 * longer exists. Shipping the film and the track together is the cheapest way
 * to guarantee they match.
 *
 * The path is written out rather than obtained from `require`, and it is a
 * plain path rather than a URL. Both of those are the result of the same
 * afternoon.
 *
 * Metro will happily bundle an mp4, but the URL it hands back resolves next to
 * the JavaScript bundle, and the player is a native GStreamer pipeline reading
 * the package mount instead. What the player can open is the contents of the
 * project's `assets/` directory, which the packager copies verbatim into the
 * package and the OS mounts at `/pkg/assets`, visible to this app and nothing
 * else. A `file://` prefix on that path fails too: the string is handed to
 * GStreamer's `filesrc` as a filename rather than parsed as a URI, so the
 * scheme becomes part of the name being looked up.
 *
 * Every one of those failures surfaces as `MEDIA_ERR_SRC_NOT_SUPPORTED`, which
 * reads like a codec problem and is really a missing file. The device log is
 * the only place the difference is visible.
 */

const PACKAGE_ASSETS = '/pkg/assets';

/** The film this build describes. */
export function filmUri(): string {
  return `${PACKAGE_ASSETS}/sintel-trailer.mp4`;
}

/**
 * The URL for a cue's pre-synthesised speech.
 *
 * Null for a cue the track names no audio for, which is survivable: the cue is
 * still scheduled and still appears on screen, it just says nothing. Silence is
 * the safe failure here, and the only one the whole design is willing to accept.
 */
export function cueAudioUri(name: string | null | undefined): string | null {
  return name ? `${PACKAGE_ASSETS}/cues/${name}` : null;
}
