export type Pane = 'issues' | 'prs' | 'pty' | 'worktrees' | 'files' | 'launch';
export type IssueFilter = 'all' | 'claim-next' | 'good first issue' | 'agent-friendly' | 'needs-validation' | 'parked';
export type SidebarItemKind = 'issue' | 'pr' | 'pty' | 'worktree' | 'file' | 'agent';

export type Selection =
  | { kind: 'issue'; id: number }
  | { kind: 'pr'; id: number }
  | { kind: 'pty'; id: string }
  | { kind: 'worktree'; id: string }
  | { kind: 'file'; id: string }
  | { kind: 'none' };

export interface ActivityItem {
  kind: 'issue' | 'pr' | 'pty';
  title: string;
  meta: string;
  ts: number;
  id: string;
}

export interface LaunchResult {
  sid?: string;
  number?: number;
}
