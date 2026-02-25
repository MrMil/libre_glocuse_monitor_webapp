import { describe, it, expect, vi } from 'vitest';
import { toDateStr, toDateTimeStr, todayStr, addDays } from '../../app/static/js/date-utils.js';

describe('toDateStr', () => {
  it('formats a date as YYYY-MM-DD using local time', () => {
    const d = new Date(2026, 0, 15, 10, 30, 0);
    expect(toDateStr(d)).toBe('2026-01-15');
  });

  it('pads single-digit month and day', () => {
    const d = new Date(2026, 2, 5, 12, 0, 0);
    expect(toDateStr(d)).toBe('2026-03-05');
  });

  it('handles December 31', () => {
    const d = new Date(2026, 11, 31, 23, 59, 0);
    expect(toDateStr(d)).toBe('2026-12-31');
  });

  it('does NOT use toISOString (prevents UTC timezone bug)', () => {
    const spy = vi.spyOn(Date.prototype, 'toISOString');
    const d = new Date(2026, 5, 15, 23, 30, 0);
    toDateStr(d);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});

describe('toDateTimeStr', () => {
  it('formats a date as YYYY-MM-DDTHH:MM:SS using local time', () => {
    const d = new Date(2026, 0, 15, 14, 5, 9);
    expect(toDateTimeStr(d)).toBe('2026-01-15T14:05:09');
  });

  it('pads all components', () => {
    const d = new Date(2026, 2, 3, 4, 5, 6);
    expect(toDateTimeStr(d)).toBe('2026-03-03T04:05:06');
  });

  it('handles midnight', () => {
    const d = new Date(2026, 0, 1, 0, 0, 0);
    expect(toDateTimeStr(d)).toBe('2026-01-01T00:00:00');
  });

  it('handles end of day', () => {
    const d = new Date(2026, 11, 31, 23, 59, 59);
    expect(toDateTimeStr(d)).toBe('2026-12-31T23:59:59');
  });

  it('does NOT use toISOString (prevents UTC timezone bug)', () => {
    const spy = vi.spyOn(Date.prototype, 'toISOString');
    const d = new Date(2026, 5, 15, 23, 30, 0);
    toDateTimeStr(d);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});

describe('todayStr', () => {
  it('returns today as YYYY-MM-DD using local time', () => {
    const now = new Date();
    const expected = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-${String(now.getDate()).padStart(2, '0')}`;
    expect(todayStr()).toBe(expected);
  });

  it('does NOT use toISOString (prevents UTC timezone bug)', () => {
    const spy = vi.spyOn(Date.prototype, 'toISOString');
    todayStr();
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});

describe('addDays', () => {
  it('adds positive days', () => {
    expect(addDays('2026-01-15', 3)).toBe('2026-01-18');
  });

  it('subtracts days with negative values', () => {
    expect(addDays('2026-01-15', -5)).toBe('2026-01-10');
  });

  it('crosses month boundary forward', () => {
    expect(addDays('2026-01-30', 3)).toBe('2026-02-02');
  });

  it('crosses month boundary backward', () => {
    expect(addDays('2026-02-02', -3)).toBe('2026-01-30');
  });

  it('crosses year boundary forward', () => {
    expect(addDays('2025-12-30', 3)).toBe('2026-01-02');
  });

  it('crosses year boundary backward', () => {
    expect(addDays('2026-01-02', -3)).toBe('2025-12-30');
  });

  it('handles adding zero days', () => {
    expect(addDays('2026-06-15', 0)).toBe('2026-06-15');
  });

  it('does NOT use toISOString (prevents UTC timezone bug)', () => {
    const spy = vi.spyOn(Date.prototype, 'toISOString');
    addDays('2026-06-15', 1);
    expect(spy).not.toHaveBeenCalled();
    spy.mockRestore();
  });
});
