import type { ReactNode } from 'react';
import type { ActivityItem, Selection } from '../types/dashboard';
import { ActivityPanel } from './ActivityPanel';

interface Counts {
  issues: number;
  prs: number;
  ptys: number;
  files: number;
}

interface InspectorPanelProps {
  counts: Counts;
  busy: string;
  selectedAgent: string;
  defaultAgent: string;
  selection: Selection;
  recentActivity: ActivityItem[];
  onFocusActivity: (item: ActivityItem) => void;
}

function Card({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2 rounded-2xl border border-border bg-card/60 p-4">
      <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{title}</div>
      <div className="flex flex-col gap-1 text-[12px] text-muted-foreground">{children}</div>
    </div>
  );
}

export function InspectorPanel({
  counts,
  busy,
  selectedAgent,
  defaultAgent,
  selection,
  recentActivity,
  onFocusActivity,
}: InspectorPanelProps) {
  return (
    <aside className="scrollbar-thin grid content-start gap-3 overflow-auto">
      <Card title="Quick facts">
        <span>{counts.issues} issues</span>
        <span>{counts.prs} PRs</span>
        <span>{counts.ptys} PTYs</span>
        <span>{counts.files} files</span>
        <span>{busy ? `Working on ${busy}` : 'Idle'}</span>
      </Card>
      <Card title="Mode">
        <span>React frontend</span>
        <span>{selectedAgent} selected</span>
        <span>{defaultAgent} default</span>
      </Card>
      <Card title="Navigation">
        <span>Selected: {selection.kind === 'none' ? 'none' : `${selection.kind}:${selection.id}`}</span>
        <span>Poll every 4s</span>
      </Card>
      <ActivityPanel items={recentActivity} onFocus={onFocusActivity} />
    </aside>
  );
}
