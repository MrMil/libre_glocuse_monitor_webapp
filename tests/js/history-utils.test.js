import { describe, it, expect } from 'vitest';
import { formatDate, groupByDay, dayStats, calcA1C, a1cColor } from '../../app/static/js/history-utils.js';

const thresholds = { urgent_low: 55, target_low: 70, target_high: 180 };

describe('formatDate', () => {
  const now = new Date('2026-02-24T12:00:00');

  it('returns "Today" for today\'s date', () => {
    expect(formatDate('2026-02-24T10:00:00', now)).toBe('Today');
  });

  it('returns "Yesterday" for yesterday\'s date', () => {
    expect(formatDate('2026-02-23T10:00:00', now)).toBe('Yesterday');
  });

  it('returns a formatted date for older dates', () => {
    const result = formatDate('2026-02-20T10:00:00', now);
    expect(result).toMatch(/Feb/);
    expect(result).toMatch(/20/);
  });
});

describe('groupByDay', () => {
  it('groups entries by calendar day', () => {
    const entries = [
      { timestamp: '2026-02-24T08:00:00', value: 100 },
      { timestamp: '2026-02-24T12:00:00', value: 110 },
      { timestamp: '2026-02-23T09:00:00', value: 90 },
    ];
    const groups = groupByDay(entries);
    expect(groups.size).toBe(2);
  });

  it('returns empty map for empty input', () => {
    const groups = groupByDay([]);
    expect(groups.size).toBe(0);
  });

  it('puts all same-day entries in one group', () => {
    const entries = [
      { timestamp: '2026-02-24T08:00:00', value: 100 },
      { timestamp: '2026-02-24T20:00:00', value: 150 },
    ];
    const groups = groupByDay(entries);
    expect(groups.size).toBe(1);
    const [items] = groups.values();
    expect(items.length).toBe(2);
  });
});

describe('dayStats', () => {
  it('computes average, range, and in-target percentage', () => {
    const entries = [
      { value: 100 },
      { value: 120 },
      { value: 140 },
    ];
    const stats = dayStats(entries, thresholds);
    expect(stats.avg).toBe(120);
    expect(stats.lo).toBe(100);
    expect(stats.hi).toBe(140);
    expect(stats.pct).toBe(100);
  });

  it('excludes boundary values from in-target count', () => {
    const entries = [
      { value: 70 },
      { value: 180 },
      { value: 100 },
    ];
    const stats = dayStats(entries, thresholds);
    expect(stats.pct).toBe(33);
  });

  it('handles all out-of-range values', () => {
    const entries = [
      { value: 200 },
      { value: 250 },
    ];
    const stats = dayStats(entries, thresholds);
    expect(stats.pct).toBe(0);
  });

  it('uses provided thresholds', () => {
    const wide = { urgent_low: 40, target_low: 50, target_high: 300 };
    const entries = [{ value: 200 }, { value: 250 }];
    const stats = dayStats(entries, wide);
    expect(stats.pct).toBe(100);
  });
});

describe('calcA1C', () => {
  const now = new Date('2026-02-24T12:00:00');

  it('calculates A1C from recent points', () => {
    const points = [
      { timestamp: '2026-02-24T08:00:00', value: 120 },
      { timestamp: '2026-02-23T08:00:00', value: 140 },
      { timestamp: '2026-02-22T08:00:00', value: 100 },
    ];
    const result = calcA1C(points, now);
    expect(result).not.toBeNull();
    expect(result.count).toBe(3);
    expect(result.avg).toBe(120);
    // (120 + 46.7) / 28.7 = 5.8
    expect(result.a1c).toBe('5.8');
  });

  it('returns null when no points are within the last week', () => {
    const points = [
      { timestamp: '2026-02-10T08:00:00', value: 120 },
    ];
    expect(calcA1C(points, now)).toBeNull();
  });

  it('filters out points older than 7 days', () => {
    const points = [
      { timestamp: '2026-02-24T08:00:00', value: 200 },
      { timestamp: '2026-02-10T08:00:00', value: 100 },
    ];
    const result = calcA1C(points, now);
    expect(result.count).toBe(1);
    expect(result.avg).toBe(200);
  });

  it('returns null for empty array', () => {
    expect(calcA1C([], now)).toBeNull();
  });

  it('computes correct A1C for known average', () => {
    // avg=154 => (154 + 46.7) / 28.7 = 6.994... => "7.0"
    const points = [
      { timestamp: '2026-02-24T08:00:00', value: 154 },
    ];
    const result = calcA1C(points, now);
    expect(result.a1c).toBe('7.0');
  });
});

describe('a1cColor', () => {
  it('returns green for A1C < 7.0', () => {
    expect(a1cColor(5.5)).toBe('var(--green)');
    expect(a1cColor(6.9)).toBe('var(--green)');
  });

  it('returns yellow for A1C >= 7.0 and < 8.0', () => {
    expect(a1cColor(7.0)).toBe('var(--yellow)');
    expect(a1cColor(7.9)).toBe('var(--yellow)');
  });

  it('returns red for A1C >= 8.0', () => {
    expect(a1cColor(8.0)).toBe('var(--red)');
    expect(a1cColor(10.0)).toBe('var(--red)');
  });
});
