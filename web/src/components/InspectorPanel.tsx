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
    <aside className="inspector">
      <div className="inspector-card">
        <div className="eyebrow">Quick facts</div>
        <div className="stack compact">
          <span>{counts.issues} issues</span>
          <span>{counts.prs} PRs</span>
          <span>{counts.ptys} PTYs</span>
          <span>{counts.files} files</span>
          <span>{busy ? `Working on ${busy}` : 'Idle'}</span>
        </div>
      </div>
      <div className="inspector-card">
        <div className="eyebrow">Mode</div>
        <div className="stack compact">
          <span>React frontend</span>
          <span>{selectedAgent} selected</span>
          <span>{defaultAgent} default</span>
        </div>
      </div>
      <div className="inspector-card">
        <div className="eyebrow">Navigation</div>
        <div className="stack compact">
          <span>Selected: {selection.kind === 'none' ? 'none' : `${selection.kind}:${selection.id}`}</span>
          <span>Poll every 4s</span>
        </div>
      </div>
      <ActivityPanel items={recentActivity} onFocus={onFocusActivity} />
    </aside>
  );
}
