// Web Worker for heavy history page computations (runs off the main thread)

function calcA1C(points) {
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

function dayStats(entries, thresholds) {
  const sorted = entries
    .map(e => ({ t: new Date(e.timestamp).getTime(), v: e.value }))
    .sort((a, b) => a.t - b.t);

  let lo = sorted[0].v, hi = sorted[0].v;
  for (let i = 1; i < sorted.length; i++) {
    if (sorted[i].v < lo) lo = sorted[i].v;
    if (sorted[i].v > hi) hi = sorted[i].v;
  }
  lo = Math.round(lo);
  hi = Math.round(hi);

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

function groupByDay(entries) {
  const groups = {};
  for (const e of entries) {
    const key = new Date(e.timestamp).toDateString();
    if (!groups[key]) groups[key] = [];
    groups[key].push(e);
  }
  return groups;
}

self.onmessage = function(e) {
  const { points, thresholds } = e.data;

  // Calculate A1C summary first and post it immediately
  const a1cResult = calcA1C(points);
  self.postMessage({ type: 'summary', a1c: a1cResult });

  // Group by day and compute per-day stats
  const groups = groupByDay(points);
  const days = [];
  for (const key of Object.keys(groups)) {
    const items = groups[key];
    if (items.length < 2) continue;
    const stats = dayStats(items, thresholds);
    days.push({ key, items, stats });
  }

  self.postMessage({ type: 'days', days });
};
