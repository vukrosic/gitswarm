import type { ReactNode } from 'react';
import type { Agent, FileEntry, Issue, PullRequest, PtySession, Worktree } from '../types';
import type { IssueFilter, Pane, Selection } from '../types/dashboard';
import { ago } from '../lib/time';
import { issueLabel, prLabel, sessionLabel } from '../lib/labels';
import { IssueFilters } from './IssueFilters';
import { PaneTabs } from './PaneTabs';

interface Counts {
  issues: number;
  prs: number;
  ptys: number;
  worktrees: number;
  files: number;
}

type SidebarEntry =
  | { kind: 'issue'; key: string; label: string; meta: string; item: Issue }
  | { kind: 'pr'; key: string; label: string; meta: string; item: PullRequest }
  | { kind: 'pty'; key: string; label: string; meta: string; item: PtySession }
  | { kind: 'worktree'; key: string; label: string; meta: string; item: Worktree }
  | { kind: 'file'; key: string; label: string; meta: string; item: FileEntry }
  | { kind: 'agent'; key: string; label: string; meta: string; item: Agent };

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

  const activeItems = (() => {
    switch (pane) {
      case 'issues':
        return visibleIssues.map((item): SidebarEntry => ({
          kind: 'issue',
          key: String(item.number),
          label: issueLabel(item),
          meta: item.claim_next ? 'claim-next' : item.in_progress ? 'in-progress' : item.parked ? 'parked' : item.state,
          item,
        }));
      case 'prs':
        return prs.map((item): SidebarEntry => ({ kind: 'pr', key: String(item.number), label: prLabel(item), meta: item.ci || item.state, item }));
      case 'pty':
        return ptys.map((item): SidebarEntry => ({ kind: 'pty', key: item.sid, label: sessionLabel(item), meta: `${item.kind || 'pty'} · ${item.alive ? 'alive' : 'dead'} · ${ago(item.last_output)}`, item }));
      case 'worktrees':
        return worktrees.map((item): SidebarEntry => ({ kind: 'worktree', key: item.name, label: item.name, meta: `${item.status} · ${item.branch}`, item }));
      case 'files':
        return files.map((item): SidebarEntry => ({ kind: 'file', key: item.name, label: item.name, meta: `${Math.round(item.size / 1024)} KB`, item }));
      case 'launch':
        return agents.map((item): SidebarEntry => ({ kind: 'agent', key: item.id, label: item.label, meta: item.available ? item.bin : 'missing', item }));
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

  return (
    <aside className="sidebar">
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
      <div className="sidebar-summary">
        <span>{counts.issues} issues</span>
        <span>{visibleIssues.length} visible</span>
        <span>{visibleClaimCount} claimable</span>
        <span>{counts.prs} prs</span>
        <span>{counts.ptys} terminals</span>
        <span>{counts.worktrees} worktrees</span>
      </div>
      {pane === 'issues' ? <IssueFilters value={issueFilter} onChange={onIssueFilterChange} /> : null}
      <div className="sidebar-toolbar">{toolbar}</div>
      <div className="list">
        {activeItems.map((entry) => (
          <div
            key={entry.key}
            className={`list-row ${isSelected(entry) ? 'active' : ''}`}
            role="button"
            tabIndex={0}
            onClick={() => focusEntry(entry)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' || event.key === ' ') {
                event.preventDefault();
                focusEntry(entry);
              }
            }}
          >
            <div className="row-top">
              <strong>{entry.label}</strong>
              <span>{entry.meta}</span>
            </div>
            <div className="row-actions">
              {entry.kind === 'issue' ? (
                <>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onClaimIssue(entry.item); }}>Claim</button>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onReviewIssue(entry.item); }}>Review</button>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onIssueTerminal(entry.item); }}>Terminal</button>
                </>
              ) : null}
              {entry.kind === 'pr' ? (
                <>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onReviewPr(entry.item); }}>Review</button>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onMergePr(entry.item); }}>Merge</button>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onFixCi(entry.item); }}>Fix CI</button>
                </>
              ) : null}
              {entry.kind === 'pty' ? (
                <>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onFocusPty(entry.item); }}>Focus</button>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onClosePty(entry.item); }}>Close</button>
                  <button type="button" className="danger" onClick={(event) => { event.stopPropagation(); onDeletePty(entry.item); }}>Delete</button>
                </>
              ) : null}
              {entry.kind === 'worktree' ? (
                <>
                  <button type="button" onClick={(event) => { event.stopPropagation(); onWorktreeShell(entry.item); }}>Shell</button>
                  <button type="button" className="danger" onClick={(event) => { event.stopPropagation(); onWorktreeRemove(entry.item); }}>Remove</button>
                </>
              ) : null}
            </div>
          </div>
        ))}
      </div>
    </aside>
  );
}
