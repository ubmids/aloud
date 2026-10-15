import {describerName, provenance, voiceName} from '../src/provenance';

test('model IDs become names a viewer can use', () => {
  expect(describerName('qwen3-vl-4b (local, llama.cpp on CPU)')).toBe('Qwen3-VL, an open model');
  expect(describerName('claude-haiku-4-5-20251001 (hosted)')).toBe('Claude Haiku 4.5');
  expect(describerName('gemini-2.5-flash')).toBe('Gemini 2.5 Flash');
  expect(voiceName('Kokoro 82M (af_heart)')).toBe('Kokoro');
});

test('a track with no record still says something true', () => {
  expect(provenance('', '')).toBe('Described ahead of time by the aloud pipeline.');
  expect(provenance('claude-haiku-4-5-20251001 (hosted)', 'Kokoro 82M (af_heart)'))
    .toBe('Described ahead of time by Claude Haiku 4.5. Read by Kokoro.');
});
