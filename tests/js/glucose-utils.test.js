import { describe, it, expect } from 'vitest';
import { glucoseClass, glucoseColor, trendLabel, formatTime } from '../../app/static/js/glucose-utils.js';

const thresholds = { urgent_low: 55, target_low: 70, target_high: 180 };

describe('glucoseClass', () => {
  it('returns "high" when value >= target_high', () => {
    expect(glucoseClass(180, thresholds)).toBe('high');
    expect(glucoseClass(250, thresholds)).toBe('high');
  });

  it('returns "urgent-low" when value <= urgent_low', () => {
    expect(glucoseClass(55, thresholds)).toBe('urgent-low');
    expect(glucoseClass(40, thresholds)).toBe('urgent-low');
  });

  it('returns "low" when value <= target_low but > urgent_low', () => {
    expect(glucoseClass(70, thresholds)).toBe('low');
    expect(glucoseClass(60, thresholds)).toBe('low');
  });

  it('returns "normal" for in-range values', () => {
    expect(glucoseClass(100, thresholds)).toBe('normal');
    expect(glucoseClass(71, thresholds)).toBe('normal');
    expect(glucoseClass(179, thresholds)).toBe('normal');
  });

  it('works with custom thresholds', () => {
    const custom = { urgent_low: 40, target_low: 60, target_high: 200 };
    expect(glucoseClass(190, custom)).toBe('normal');
    expect(glucoseClass(200, custom)).toBe('high');
  });
});

describe('glucoseColor', () => {
  it('returns red for high values', () => {
    expect(glucoseColor(180, thresholds)).toBe('#ef4444');
    expect(glucoseColor(300, thresholds)).toBe('#ef4444');
  });

  it('returns red for urgent low values', () => {
    expect(glucoseColor(55, thresholds)).toBe('#ef4444');
    expect(glucoseColor(30, thresholds)).toBe('#ef4444');
  });

  it('returns yellow for low values', () => {
    expect(glucoseColor(70, thresholds)).toBe('#eab308');
    expect(glucoseColor(60, thresholds)).toBe('#eab308');
  });

  it('returns green for normal values', () => {
    expect(glucoseColor(100, thresholds)).toBe('#22c55e');
    expect(glucoseColor(179, thresholds)).toBe('#22c55e');
  });
});

describe('trendLabel', () => {
  it('maps known trend names', () => {
    expect(trendLabel('DOWN_FAST')).toBe('Falling fast');
    expect(trendLabel('DOWN_SLOW')).toBe('Falling');
    expect(trendLabel('STABLE')).toBe('Stable');
    expect(trendLabel('UP_SLOW')).toBe('Rising');
    expect(trendLabel('UP_FAST')).toBe('Rising fast');
  });

  it('returns unknown names as-is', () => {
    expect(trendLabel('UNKNOWN')).toBe('UNKNOWN');
    expect(trendLabel('')).toBe('');
  });
});

describe('formatTime', () => {
  it('formats an ISO timestamp to HH:MM', () => {
    const result = formatTime('2026-02-24T14:30:00');
    expect(result).toMatch(/14:30|2:30/);
  });

  it('handles midnight', () => {
    const result = formatTime('2026-02-24T00:00:00');
    expect(result).toMatch(/00:00|12:00/);
  });
});
