import type { ActivityItem } from '../types/dashboard';
import { ago } from '../lib/time';

interface ActivityPanelProps {
  items: ActivityItem[];
  onFocus: (item: ActivityItem) => void;
}

export function ActivityPanel({ items, onFocus }: ActivityPanelProps) {
  return (
    <div className="flex flex-col gap-2.5 rounded-2xl border border-border bg-card/60 p-4">
      <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Activity</div>
      <div className="flex flex-col gap-1.5">
        {items.length ? (
          items.map((item) => (
            <button
              key={`${item.kind}:${item.id}`}
              onClick={() => onFocus(item)}
              className="group flex flex-col gap-0.5 rounded-xl border border-border/80 bg-card/60 px-2.5 py-2 text-left transition-all hover:-translate-y-px hover:border-primary/50 hover:bg-card"
            >
              <strong className="text-[12px] font-medium leading-tight text-foreground">{item.title}</strong>
              <span className="text-[11px] text-muted-foreground">
                {item.meta} · {ago(Math.floor(item.ts / 1000))}
              </span>
            </button>
          ))
        ) : (
          <span className="text-[11px] text-muted-foreground">nothing recent yet</span>
        )}
      </div>
    </div>
  );
}
