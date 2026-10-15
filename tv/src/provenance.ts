/**
 * Who described a film and whose voice reads it, in words a viewer can use.
 *
 * Tracks record the model and voice exactly ("qwen3-vl-4b (local, llama.cpp on
 * CPU)", "Kokoro 82M (af_heart)"), which is right for the record and wrong for
 * a sofa. The shelf names them the way a person would, and never shows a model
 * ID, a quantisation or a voice code.
 */

export function describerName(raw: string | undefined): string {
  const id = (raw ?? '').replace(/\s*\(.*\)\s*$/, '').trim();
  if (!id) return '';
  let m = /^qwen(\d+(?:\.\d+)?)-vl/i.exec(id);
  if (m) return `Qwen${m[1]}-VL, an open model`;
  m = /^claude-([a-z]+)-(\d+)-(\d+)/i.exec(id);
  if (m) return `Claude ${m[1][0].toUpperCase()}${m[1].slice(1)} ${m[2]}.${m[3]}`;
  m = /^gemini-(\d+(?:\.\d+)?)-([a-z]+)/i.exec(id);
  if (m) return `Gemini ${m[1]} ${m[2][0].toUpperCase()}${m[2].slice(1)}`;
  // Anything else: the name without its date stamp or size suffix.
  return id.replace(/-\d{8}$/, '').replace(/[-_]/g, ' ');
}

export function voiceName(raw: string | undefined): string {
  return (raw ?? '')
    .replace(/\s*\(.*\)\s*$/, '')
    .replace(/\s+\d+(?:\.\d+)?[MB]\b/i, '')
    .trim();
}

export function provenance(describer?: string, voice?: string): string {
  const who = describerName(describer);
  const said = voiceName(voice);
  const first = who
    ? `Described ahead of time by ${who}.`
    : 'Described ahead of time by the aloud pipeline.';
  return said ? `${first} Read by ${said}.` : first;
}
