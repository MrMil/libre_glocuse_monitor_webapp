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
  const sorted = entries
    .map(e => ({ t: new Date(e.timestamp).getTime(), v: e.value }))
    .sort((a, b) => a.t - b.t);

  const lo = Math.round(Math.min(...sorted.map(p => p.v)));
  const hi = Math.round(Math.max(...sorted.map(p => p.v)));

  if (sorted.length < 2) {
    const v = sorted[0].v;
    const inRange = v > thresholds.target_low && v < thresholds.target_high;
    return { avg: Math.round(v), lo, hi, pct: inRange ? 100 : 0 };
  }

  let weightedSum = 0;
  let inRangeDuration = 0;
  let totalDuration = 0;

  for (let i = 1; i < sorted.length; i++) {
    const dt = sorted[i].t - sorted[i - 1].t;
    const segAvg = (sorted[i].v + sorted[i - 1].v) / 2;
    weightedSum += segAvg * dt;
    totalDuration += dt;
    if (segAvg > thresholds.target_low && segAvg < thresholds.target_high) {
      inRangeDuration += dt;
    }
  }

  const avg = Math.round(weightedSum / totalDuration);
  const pct = Math.round((inRangeDuration / totalDuration) * 100);
  return { avg, lo, hi, pct };
}

export function calcA1C(points) {
  const sorted = points
    .map(p => ({ t: new Date(p.timestamp).getTime(), v: p.value }))
    .sort((a, b) => a.t - b.t);

  if (sorted.length === 0) return null;

  if (sorted.length === 1) {
    const a1c = (sorted[0].v + 46.7) / 28.7;
    return { a1c: a1c.toFixed(1), avg: Math.round(sorted[0].v), count: 1 };
  }

  let weightedSum = 0;
  let totalDuration = 0;

  for (let i = 1; i < sorted.length; i++) {
    const dt = sorted[i].t - sorted[i - 1].t;
    weightedSum += (sorted[i].v + sorted[i - 1].v) / 2 * dt;
    totalDuration += dt;
  }

  const avg = weightedSum / totalDuration;
  const a1c = (avg + 46.7) / 28.7;
  return { a1c: a1c.toFixed(1), avg: Math.round(avg), count: sorted.length };
}

export function a1cColor(a1c) {
  if (a1c < 7.0) return 'var(--green)';
  if (a1c < 8.0) return 'var(--yellow)';
  return 'var(--red)';
}
