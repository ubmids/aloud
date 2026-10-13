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

/**
 * Each title has a folder of its own: `assets/films/<id>/` holds `film.mp4`,
 * `cues/` with one spoken file per description, and `announce.m4a`, the title
 * read aloud for the shelf. The trailer's film is small enough to live in the
 * repository; the full-length films are fetched and encoded by
 * `python3 -m aloud.films fetch`, from the Blender Foundation's own mirror.
 */
function folder(id: string): string {
  return `${PACKAGE_ASSETS}/films/${id}`;
}

/** The film a title plays. */
export function filmUri(id: string): string {
  return `${folder(id)}/film.mp4`;
}

/**
 * The URL for a cue's pre-synthesised speech.
 *
 * Null for a cue the track names no audio for, which is survivable: the cue is
 * still scheduled and still appears on screen, it just says nothing. Silence is
 * the safe failure here, and the only one the whole design is willing to accept.
 */
export function cueAudioUri(id: string, name: string | null | undefined): string | null {
  return name ? `${folder(id)}/cues/${name}` : null;
}

/** The title, spoken, for when it takes focus on the shelf. */
export function announceUri(id: string): string {
  return `${folder(id)}/announce.m4a`;
}
