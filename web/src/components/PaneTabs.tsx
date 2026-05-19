import { FileText, Flag, GitBranch, GitPullRequest, Grid, ListChecks, Rocket, Terminal as TerminalIcon, Bell } from 'lucide-react';
import type { ComponentType, SVGProps } from 'react';
import { cn } from '@/lib/utils';
import type { Pane } from '../types/dashboard';

type IconType = ComponentType<SVGProps<SVGSVGElement>>;

export const PANES: Array<{ key: Pane; label: string; icon: IconType }> = [
  { key: 'issues', label: 'Issues', icon: ListChecks },
  { key: 'milestones', label: 'Milestones', icon: Flag },
  { key: 'prs', label: 'PRs', icon: GitPullRequest },
  { key: 'pty', label: 'Terminals', icon: TerminalIcon },
  { key: 'worktrees', label: 'Worktrees', icon: GitBranch },
  { key: 'files', label: 'Files', icon: FileText },
  { key: 'launch', label: 'Launch', icon: Rocket },
  { key: 'agent-grid', label: 'Agent Grid', icon: Grid },
  { key: 'notifications', label: 'Notifications', icon: Bell },
];

interface PaneTabsProps {
  value: Pane;
  onChange: (value: Pane) => void;
  counts?: Partial<Record<Pane, number>>;
}

export function PaneTabs({ value, onChange, counts }: PaneTabsProps) {
  return (
    <div className="grid grid-cols-2 gap-2 border-b border-border/60 bg-background/30 p-3">
      {PANES.map(({ key, label, icon: Icon }) => {
        const active = value === key;
        const count = counts?.[key];
        return (
          <button
            key={key}
            type="button"
            onClick={() => onChange(key)}
            className={cn(
              'group inline-flex items-center justify-between gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
              active
                ? 'border-primary/60 bg-gradient-to-b from-primary/20 to-primary/5 text-foreground shadow-[inset_0_1px_0_hsl(0_0%_100%/0.05),0_8px_18px_hsl(213_94%_50%/0.18)]'
                : 'border-border bg-card/40 text-muted-foreground hover:border-primary/40 hover:bg-accent hover:text-foreground',
            )}
          >
            <span className="flex items-center gap-1.5">
              <Icon className="h-3.5 w-3.5" />
              {label}
            </span>
            {typeof count === 'number' ? (
              <span
                className={cn(
                  'min-w-[1.6rem] rounded-full px-1.5 py-0.5 text-center text-[10px] font-semibold leading-none',
                  active
                    ? 'bg-primary/25 text-primary-foreground/95'
                    : 'bg-accent text-muted-foreground group-hover:text-foreground',
                )}
              >
                {count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
