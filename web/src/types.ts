export type Id = string;

export interface LabelledItem {
  labels: string[];
}

export interface Issue extends LabelledItem {
  number: number;
  title: string;
  body: string;
  state: string;
  assignees: string[];
  created_at: string;
  updated_at: string;
  in_progress: boolean;
  claim_next?: boolean;
  parked?: boolean;
  summary?: string;
  suggested_labels?: string[];
  url?: string;
  author?: string;
  comment_count?: number;
}

export interface PullRequest extends LabelledItem {
  number: number;
  title: string;
  body: string;
  state: string;
  author: string;
  base: string;
  head: string;
  url: string;
  additions?: number;
  deletions?: number;
  isDraft?: boolean;
  reviewDecision?: string;
  mergeable?: string | null;
  ci?: string;
  failing_checks?: string[];
  pending_checks?: string[];
  summary?: string;
  reviewed_by_codex?: boolean;
}

export interface Worktree {
  name: string;
  branch: string;
  commits: string;
  ahead: number;
  behind: number;
  status: string;
  safe_remove?: boolean;
}

export interface FileEntry {
  name: string;
  size: number;
  mtime: number;
}

export interface PtySession {
  sid: string;
  label: string;
  cwd: string;
  alive: boolean;
  kind?: string;
  issue?: number | null;
  pr?: number | null;
  started?: number;
  last_output?: number;
  last_input?: number;
  rows?: number;
  cols?: number;
}

export interface Agent {
  id: string;
  label: string;
  bin: string;
  model: string;
  available: boolean;
}

export interface Snapshot {
  issues: Issue[];
  prs: PullRequest[];
  worktrees: Worktree[];
  files: FileEntry[];
  ptys: PtySession[];
  agents: Agent[];
  defaultAgent: string;
  codeMtime: number;
}

export interface PtyStreamResult {
  text: string;
  offset: number;
  alive: boolean;
  drop: number;
  reset: boolean;
}
