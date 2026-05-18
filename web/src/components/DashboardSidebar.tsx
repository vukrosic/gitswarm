import type { ReactNode } from 'react';
import type { Agent, FileEntry, Issue, PullRequest, PtySession, Worktree } from '../types';
import type { IssueFilter, Pane, Selection } from '../types/dashboard';
import { ago } from '../lib/time';
import { issueLabel, prLabel, sessionLabel } from '../lib/labels';
import { IssueFilters } from './IssueFilters';
import { PaneTabs } from './PaneTabs';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface Counts {
  issues: number;
  prs: number;
  ptys: number;
  worktrees: number;
  files: number;
}

type SidebarEntry =
  | { kind: 'issue'; key: string; label: string; meta: string; tone: 'default' | 'success' | 'warning' | 'muted'; item: Issue }
  | { kind: 'pr'; key: string; label: string; meta: string; tone: 'default' | 'success' | 'warning' | 'destructive'; item: PullRequest }
  | { kind: 'pty'; key: string; label: string; meta: string; tone: 'default' | 'success' | 'muted'; item: PtySession }
  | { kind: 'worktree'; key: string; label: string; meta: string; tone: 'default'; item: Worktree }
  | { kind: 'file'; key: string; label: string; meta: string; tone: 'default'; item: FileEntry }
  | { kind: 'agent'; key: string; label: string; meta: string; tone: 'success' | 'destructive'; item: Agent };

interface DashboardSidebarProps {
  pane: Pane;
  counts: Counts;
  visibleIssues: Issue[];
  visibleClaimCount: number;
  issueFilter: IssueFilter;
  selection: Selection;
  prs: PullRequest[];
  ptys: PtySession[];
  worktrees: Worktree[];
  files: FileEntry[];
  agents: Agent[];
  selectedAgent: string;
  toolbar: ReactNode;
  onPaneChange: (pane: Pane) => void;
  onIssueFilterChange: (filter: IssueFilter) => void;
  onSelect: (selection: Selection) => void;
  onFocusPty: (pty: PtySession) => void;
  onSelectAgent: (agent: string) => void;
  onClaimIssue: (issue: Issue) => void;
  onReviewIssue: (issue: Issue) => void;
  onIssueTerminal: (issue: Issue) => void;
  onReviewPr: (pr: PullRequest) => void;
  onMergePr: (pr: PullRequest) => void;
  onFixCi: (pr: PullRequest) => void;
  onClosePty: (pty: PtySession) => void;
  onDeletePty: (pty: PtySession) => void;
  onWorktreeShell: (worktree: Worktree) => void;
  onWorktreeRemove: (worktree: Worktree) => void;
}

const TONE_DOT: Record<string, string> = {
  default: 'bg-muted-foreground/40',
  success: 'bg-success',
  warning: 'bg-warning',
  destructive: 'bg-destructive',
  muted: 'bg-muted-foreground/30',
};

export function DashboardSidebar(props: DashboardSidebarProps) {
  const {
    pane,
    counts,
    visibleIssues,
    visibleClaimCount,
    issueFilter,
    selection,
    prs,
    ptys,
    worktrees,
    files,
    agents,
    selectedAgent,
    toolbar,
    onPaneChange,
    onIssueFilterChange,
    onSelect,
    onFocusPty,
    onSelectAgent,
    onClaimIssue,
    onReviewIssue,
    onIssueTerminal,
    onReviewPr,
    onMergePr,
    onFixCi,
    onClosePty,
    onDeletePty,
    onWorktreeShell,
    onWorktreeRemove,
  } = props;

  const activeItems = ((): SidebarEntry[] => {
    switch (pane) {
      case 'issues':
        return visibleIssues.map((item): SidebarEntry => {
          const tone: SidebarEntry['tone'] = item.claim_next
            ? 'success'
            : item.in_progress
              ? 'warning'
              : item.parked
                ? 'muted'
                : 'default';
          return {
            kind: 'issue',
            key: String(item.number),
            label: issueLabel(item),
            meta: item.claim_next ? 'claim-next' : item.in_progress ? 'in-progress' : item.parked ? 'parked' : item.state,
            tone,
            item,
          };
        });
      case 'prs':
        return prs.map((item): SidebarEntry => {
          const tone: SidebarEntry['tone'] =
            item.ci === 'ok'
              ? 'success'
              : item.ci === 'pending'
                ? 'warning'
                : item.ci === 'fail'
                  ? 'destructive'
                  : 'default';
          return { kind: 'pr', key: String(item.number), label: prLabel(item), meta: item.ci || item.state, tone, item };
        });
      case 'pty':
        return ptys.map((item): SidebarEntry => ({
          kind: 'pty',
          key: item.sid,
          label: sessionLabel(item),
          meta: `${item.kind || 'pty'} · ${item.alive ? 'alive' : 'dead'} · ${ago(item.last_output)}`,
          tone: item.alive ? 'success' : 'muted',
          item,
        }));
      case 'worktrees':
        return worktrees.map((item): SidebarEntry => ({
          kind: 'worktree',
          key: item.name,
          label: item.name,
          meta: `${item.status} · ${item.branch}`,
          tone: 'default',
          item,
        }));
      case 'files':
        return files.map((item): SidebarEntry => ({
          kind: 'file',
          key: item.name,
          label: item.name,
          meta: `${Math.round(item.size / 1024)} KB`,
          tone: 'default',
          item,
        }));
      case 'launch':
        return agents.map((item): SidebarEntry => ({
          kind: 'agent',
          key: item.id,
          label: item.label,
          meta: item.available ? item.bin : 'missing',
          tone: item.available ? 'success' : 'destructive',
          item,
        }));
      default:
        return [];
    }
  })();

  function isSelected(entry: SidebarEntry) {
    return (
      (entry.kind === 'issue' && selection.kind === 'issue' && selection.id === Number(entry.key)) ||
      (entry.kind === 'pr' && selection.kind === 'pr' && selection.id === Number(entry.key)) ||
      (entry.kind === 'pty' && selection.kind === 'pty' && selection.id === entry.key) ||
      (entry.kind === 'worktree' && selection.kind === 'worktree' && selection.id === entry.key) ||
      (entry.kind === 'file' && selection.kind === 'file' && selection.id === entry.key) ||
      (entry.kind === 'agent' && selectedAgent === entry.key)
    );
  }

  function focusEntry(entry: SidebarEntry) {
    if (entry.kind === 'issue') onSelect({ kind: 'issue', id: Number(entry.key) });
    else if (entry.kind === 'pr') onSelect({ kind: 'pr', id: Number(entry.key) });
    else if (entry.kind === 'pty') onFocusPty(entry.item);
    else if (entry.kind === 'worktree') onSelect({ kind: 'worktree', id: entry.key });
    else if (entry.kind === 'file') onSelect({ kind: 'file', id: entry.key });
    else onSelectAgent(entry.key);
  }

  const summary = [
    { label: 'issues', value: counts.issues },
    { label: 'visible', value: visibleIssues.length },
    { label: 'claimable', value: visibleClaimCount },
    { label: 'prs', value: counts.prs },
    { label: 'terminals', value: counts.ptys },
    { label: 'worktrees', value: counts.worktrees },
  ];

  return (
    <aside className="flex min-h-0 flex-col overflow-hidden rounded-[var(--radius)] border border-border bg-gradient-to-b from-card/90 to-background/95 shadow-[0_24px_70px_hsl(0_0%_0%/0.42)] backdrop-blur-xl">
      <PaneTabs
        value={pane}
        onChange={onPaneChange}
        counts={{
          issues: counts.issues,
          prs: counts.prs,
          pty: counts.ptys,
          worktrees: counts.worktrees,
          files: counts.files,
          launch: agents.length,
        }}
      />

      <div className="flex flex-wrap gap-1.5 px-3 pt-3 text-[11px] text-muted-foreground">
        {summary.map((item) => (
          <span
            key={item.label}
            className="inline-flex items-center gap-1 rounded-full border border-border/70 bg-card/40 px-2 py-0.5 tabular-nums"
          >
            <strong className="font-semibold text-foreground">{item.value}</strong>
            {item.label}
          </span>
        ))}
      </div>

      {pane === 'issues' ? <IssueFilters value={issueFilter} onChange={onIssueFilterChange} /> : null}

      {toolbar ? (
        <div className="flex flex-wrap gap-1.5 border-b border-border/50 px-3 py-3 [&_button]:rounded-full [&_button]:border [&_button]:border-border [&_button]:bg-card/40 [&_button]:px-2.5 [&_button]:py-1 [&_button]:text-[11px] [&_button]:text-muted-foreground [&_button]:transition-colors [&_button:hover]:border-primary/50 [&_button:hover]:text-foreground [&_button.danger]:text-destructive">
          {toolbar}
        </div>
      ) : null}

      <div className="scrollbar-thin grid gap-1.5 overflow-auto p-3">
        {activeItems.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border/60 bg-card/30 p-4 text-center text-xs text-muted-foreground">
            Nothing here yet.
          </div>
        ) : null}

        {activeItems.map((entry) => {
          const selected = isSelected(entry);
          return (
            <div
              key={entry.key}
              role="button"
              tabIndex={0}
              onClick={() => focusEntry(entry)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' || event.key === ' ') {
                  event.preventDefault();
                  focusEntry(entry);
                }
              }}
              className={cn(
                'group relative flex cursor-pointer flex-col gap-2 rounded-2xl border px-3 py-2.5 text-left transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
                selected
                  ? 'border-primary/70 bg-gradient-to-b from-primary/15 to-background/40 shadow-[inset_3px_0_0_hsl(var(--primary)),0_12px_26px_hsl(0_0%_0%/0.25)]'
                  : 'border-border/80 bg-card/60 hover:-translate-y-px hover:border-primary/40 hover:bg-card',
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  <span className={cn('h-2 w-2 shrink-0 rounded-full', TONE_DOT[entry.tone] || TONE_DOT.default)} />
                  <strong className="truncate text-[13px] font-medium leading-snug tracking-tight text-foreground">
                    {entry.label}
                  </strong>
                </div>
                <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground">
                  {entry.meta}
                </span>
              </div>

              {entry.kind === 'issue' || entry.kind === 'pr' || entry.kind === 'pty' || entry.kind === 'worktree' ? (
                <div className="flex flex-wrap gap-1">
                  {entry.kind === 'issue' ? (
                    <>
                      <RowButton onClick={(e) => { e.stopPropagation(); onClaimIssue(entry.item); }}>Claim</RowButton>
                      <RowButton onClick={(e) => { e.stopPropagation(); onReviewIssue(entry.item); }}>Review</RowButton>
                      <RowButton onClick={(e) => { e.stopPropagation(); onIssueTerminal(entry.item); }}>Terminal</RowButton>
                    </>
                  ) : null}
                  {entry.kind === 'pr' ? (
                    <>
                      <RowButton onClick={(e) => { e.stopPropagation(); onReviewPr(entry.item); }}>Review</RowButton>
                      <RowButton onClick={(e) => { e.stopPropagation(); onMergePr(entry.item); }}>Merge</RowButton>
                      <RowButton onClick={(e) => { e.stopPropagation(); onFixCi(entry.item); }}>Fix CI</RowButton>
                    </>
                  ) : null}
                  {entry.kind === 'pty' ? (
                    <>
                      <RowButton onClick={(e) => { e.stopPropagation(); onFocusPty(entry.item); }}>Focus</RowButton>
                      <RowButton onClick={(e) => { e.stopPropagation(); onClosePty(entry.item); }}>Close</RowButton>
                      <RowButton danger onClick={(e) => { e.stopPropagation(); onDeletePty(entry.item); }}>Delete</RowButton>
                    </>
                  ) : null}
                  {entry.kind === 'worktree' ? (
                    <>
                      <RowButton onClick={(e) => { e.stopPropagation(); onWorktreeShell(entry.item); }}>Shell</RowButton>
                      <RowButton danger onClick={(e) => { e.stopPropagation(); onWorktreeRemove(entry.item); }}>Remove</RowButton>
                    </>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </aside>
  );
}

function RowButton({
  children,
  danger,
  onClick,
}: {
  children: ReactNode;
  danger?: boolean;
  onClick: (event: React.MouseEvent<HTMLButtonElement>) => void;
}) {
  return (
    <Button
      type="button"
      variant={danger ? 'danger' : 'outline'}
      size="sm"
      className="h-6 px-2 text-[10px]"
      onClick={onClick}
    >
      {children}
    </Button>
  );
}
