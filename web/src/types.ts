export type Id = string;

export interface LabelledItem {
  labels: string[];
}

export interface MilestoneRef {
  number: number;
  title: string;
  state: string;
  due_on?: string | null;
}

export interface Milestone extends MilestoneRef {
  description?: string;
  open_issues: number;
  closed_issues: number;
  created_at?: string;
  updated_at?: string;
  url?: string;
}

export interface GitHubComment {
  id?: number;
  author: string;
  body: string;
  url?: string;
  created_at: string;
  updated_at?: string;
}

export interface GitHubReview {
  id?: number;
  author: string;
  state: string;
  body: string;
  url?: string;
  submitted_at: string;
}

export interface GitHubReviewComment extends GitHubComment {
  path?: string;
  line?: number | null;
  diff_hunk?: string;
}

export interface GitHubNotification {
  id: string;
  reason: string;
  unread: boolean;
  updated_at: string;
  subject_title: string;
  subject_type: string;
  subject_url: string;
  repository_name: string;
  repository_full_name: string;
}

export interface Project {
  id: string;
  label: string;
  repo_root: string;
  repo_name: string;
  github_slug: string;
  state_dir: string;
  worktree_dir: string;
  exists?: boolean;
  active?: boolean;
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
  comments?: GitHubComment[];
  milestone?: MilestoneRef | null;
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
  comments?: GitHubComment[];
  reviews?: GitHubReview[];
  review_comments?: GitHubReviewComment[];
}

export interface Worktree {
  name: string;
  path?: string;
  branch: string;
  head?: string;
  commits: string;
  ahead: number;
  behind: number;
  status: string;
  dirty?: boolean;
  merged?: boolean;
  safe_remove?: boolean;
  running?: boolean;
  issue?: number | null;
}

export interface RunningWorktree {
  issue: string;
  worktree: string;
  active: boolean;
}

export interface FileEntry {
  name: string;
  size: number;
  mtime: number;
}

export interface GridSession {
  sid: string;
  issue?: number | null;
  label: string;
  alive: boolean;
  cwd: string;
  kind?: string;
  started?: number;
  last_output?: number;
  rows?: number;
  cols?: number;
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
  milestones: Milestone[];
  prs: PullRequest[];
  worktrees: Worktree[];
  running?: RunningWorktree[];
  files: FileEntry[];
  ptys: PtySession[];
  agents: Agent[];
  defaultAgent: string;
  codeMtime: number;
  codeMtimePath?: string;
}

export interface AgentGridState {
  sessions: GridSession[];
  launched: boolean;
  agent: string;
  gridSessions: GridSession[];
  loading: boolean;
}

export interface PtyStreamResult {
  text: string;
  offset: number;
  alive: boolean;
  drop: number;
  reset: boolean;
}
