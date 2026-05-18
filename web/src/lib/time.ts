export function ago(ts?: number): string {
  if (!ts) return 'just now';
  const diff = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (diff < 5) return 'just now';
  if (diff < 60) return `${diff}s ago`;
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function fmtTime(ts?: number): string {
  if (!ts) return '';
  return new Date(ts * 1000).toLocaleString();
}
