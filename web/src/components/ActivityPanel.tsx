import type { ActivityItem } from '../types/dashboard';
import { ago } from '../lib/time';

interface ActivityPanelProps {
  items: ActivityItem[];
  onFocus: (item: ActivityItem) => void;
}

export function ActivityPanel({ items, onFocus }: ActivityPanelProps) {
  return (
    <div className="inspector-card">
      <div className="eyebrow">Activity</div>
      <div className="stack compact">
        {items.length ? items.map((item) => (
          <button
            key={`${item.kind}:${item.id}`}
            className="activity-row"
            onClick={() => onFocus(item)}
          >
            <strong>{item.title}</strong>
            <span>{item.meta} · {ago(Math.floor(item.ts / 1000))}</span>
          </button>
        )) : <span>nothing recent yet</span>}
      </div>
    </div>
  );
}
