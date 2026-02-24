export function glucoseClass(value, thresholds) {
  if (value >= thresholds.target_high) return 'high';
  if (value <= thresholds.urgent_low) return 'urgent-low';
  if (value <= thresholds.target_low) return 'low';
  return 'normal';
}

export function glucoseColor(value, thresholds) {
  if (value >= thresholds.target_high) return '#ef4444';
  if (value <= thresholds.urgent_low) return '#ef4444';
  if (value <= thresholds.target_low) return '#eab308';
  return '#22c55e';
}

export function trendLabel(name) {
  const map = {
    'DOWN_FAST': 'Falling fast',
    'DOWN_SLOW': 'Falling',
    'STABLE': 'Stable',
    'UP_SLOW': 'Rising',
    'UP_FAST': 'Rising fast',
  };
  return map[name] || name;
}

export function formatTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}
