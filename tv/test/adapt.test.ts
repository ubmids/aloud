import {ASK_WINDOW_MS, remember, shouldSayMore} from '../src/player/adapt';

describe('saying more when the viewer keeps asking', () => {
  test('two asks inside two minutes on the lighter setting mean say more', () => {
    const asks = remember(remember([], 0), 60_000);
    expect(shouldSayMore(asks, 'sparse')).toBe(true);
  });

  test('one ask is a question, not a pattern', () => {
    expect(shouldSayMore(remember([], 0), 'sparse')).toBe(false);
  });

  test('asks further apart than the window are forgotten', () => {
    const asks = remember(remember([], 0), ASK_WINDOW_MS + 1);
    expect(asks).toEqual([ASK_WINDOW_MS + 1]);
    expect(shouldSayMore(asks, 'sparse')).toBe(false);
  });

  test('it never turns itself down: at full there is nothing more to say', () => {
    const asks = remember(remember(remember([], 0), 1000), 2000);
    expect(shouldSayMore(asks, 'full')).toBe(false);
  });
});
