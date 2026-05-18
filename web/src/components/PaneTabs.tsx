import type { Pane } from '../types/dashboard';

export const PANES: Array<{ key: Pane; label: string }> = [
  { key: 'issues', label: 'Issues' },
  { key: 'prs', label: 'PRs' },
  { key: 'pty', label: 'Terminals' },
  { key: 'worktrees', label: 'Worktrees' },
  { key: 'files', label: 'Files' },
  { key: 'launch', label: 'Launch' },
];

interface PaneTabsProps {
  value: Pane;
  onChange: (value: Pane) => void;
  counts?: Partial<Record<Pane, number>>;
}

export function PaneTabs({ value, onChange, counts }: PaneTabsProps) {
  return (
    <div className="pane-tabs">
      {PANES.map((item) => (
        <button key={item.key} className={value === item.key ? 'on' : ''} onClick={() => onChange(item.key)}>
          <span>{item.label}</span>
          {typeof counts?.[item.key] === 'number' ? <strong>{counts[item.key]}</strong> : null}
        </button>
      ))}
    </div>
  );
}
