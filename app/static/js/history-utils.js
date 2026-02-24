export function formatDate(iso, now = new Date()) {
  const d = new Date(iso);
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);

  if (d.toDateString() === now.toDateString()) return 'Today';
  if (d.toDateString() === yesterday.toDateString()) return 'Yesterday';
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
}

export function groupByDay(entries) {
  const groups = new Map();
  for (const e of entries) {
    const key = new Date(e.timestamp).toDateString();
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(e);
  }
  return groups;
}

export function dayStats(entries, thresholds) {
  const values = entries.map(e => e.value);
  const avg = Math.round(values.reduce((a, b) => a + b, 0) / values.length);
  const lo = Math.round(Math.min(...values));
  const hi = Math.round(Math.max(...values));
  const inRange = values.filter(v => v > thresholds.target_low && v < thresholds.target_high);
  const pct = Math.round((inRange.length / values.length) * 100);
  return { avg, lo, hi, pct };
}

export function calcA1C(points, now = new Date()) {
  const weekAgo = new Date(now);
  weekAgo.setDate(now.getDate() - 7);

  const weekPoints = points.filter(p => new Date(p.timestamp) >= weekAgo);
  if (weekPoints.length === 0) return null;

  const values = weekPoints.map(p => p.value);
  const avg = values.reduce((a, b) => a + b, 0) / values.length;
  const a1c = (avg + 46.7) / 28.7;
  return { a1c: a1c.toFixed(1), avg: Math.round(avg), count: weekPoints.length };
}

export function a1cColor(a1c) {
  if (a1c < 7.0) return 'var(--green)';
  if (a1c < 8.0) return 'var(--yellow)';
  return 'var(--red)';
}
