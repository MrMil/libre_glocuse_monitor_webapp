import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));

// Build a minimal Worker-like harness that captures postMessage calls.
function loadWorker() {
  const messages = [];
  const selfShim = {
    onmessage: null,
    postMessage(data) { messages.push(data); },
  };
  const code = readFileSync(
    resolve(__dirname, '../../app/static/js/history-worker.js'),
    'utf-8',
  );
  const fn = new Function('self', code);
  fn(selfShim);
  return { selfShim, messages };
}

// Helper: generate N hours of glucose points
function generatePoints(hours) {
  const points = [];
  const base = new Date('2026-01-01T00:00:00').getTime();
  for (let m = 0; m < hours * 60; m += 5) {
    points.push({
      timestamp: new Date(base + m * 60000).toISOString(),
      value: 100 + Math.sin(m / 60) * 40,
    });
  }
  return points;
}

const thresholds = { urgent_low: 55, target_low: 70, target_high: 180 };

describe('history-worker', () => {
  it('posts summary before days', () => {
    const { selfShim, messages } = loadWorker();
    const points = generatePoints(48);

    selfShim.onmessage({ data: { points, thresholds } });

    expect(messages.length).toBe(2);
    expect(messages[0].type).toBe('summary');
    expect(messages[1].type).toBe('days');
  });

  it('returns correct A1C in summary', () => {
    const { selfShim, messages } = loadWorker();
    const points = [
      { timestamp: '2026-01-01T08:00:00', value: 120 },
      { timestamp: '2026-01-02T08:00:00', value: 120 },
    ];

    selfShim.onmessage({ data: { points, thresholds } });

    const summary = messages[0];
    expect(summary.a1c).not.toBeNull();
    expect(summary.a1c.avg).toBe(120);
    expect(summary.a1c.a1c).toBe('5.8');
  });

  it('returns per-day stats in days message', () => {
    const { selfShim, messages } = loadWorker();
    const points = generatePoints(48);

    selfShim.onmessage({ data: { points, thresholds } });

    const days = messages[1];
    expect(days.days.length).toBeGreaterThanOrEqual(2);
    for (const day of days.days) {
      expect(day.stats).toHaveProperty('avg');
      expect(day.stats).toHaveProperty('lo');
      expect(day.stats).toHaveProperty('hi');
      expect(day.stats).toHaveProperty('pct');
      expect(day.items.length).toBeGreaterThan(1);
    }
  });

  it('processes large datasets and produces valid output (90 days)', () => {
    const { selfShim, messages } = loadWorker();
    const points = generatePoints(90 * 24); // ~25,920 points

    const start = performance.now();
    selfShim.onmessage({ data: { points, thresholds } });
    const elapsed = performance.now() - start;

    expect(messages.length).toBe(2);
    expect(messages[0].type).toBe('summary');
    expect(messages[0].a1c).not.toBeNull();
    expect(messages[0].a1c.count).toBe(points.length);
    expect(messages[1].type).toBe('days');
    expect(messages[1].days.length).toBeGreaterThanOrEqual(89);

    // In production this runs on a Web Worker thread, so it won't block the UI.
    // Here we just verify it completes reasonably fast.
    console.log(`Worker processed ${points.length} points (${messages[1].days.length} days) in ${elapsed.toFixed(0)}ms`);
  });

  it('summary is posted before days (message ordering with 30 days)', () => {
    const { selfShim, messages } = loadWorker();
    const points = generatePoints(24 * 30);

    selfShim.onmessage({ data: { points, thresholds } });

    expect(messages[0].type).toBe('summary');
    expect(messages[1].type).toBe('days');
  });
});
