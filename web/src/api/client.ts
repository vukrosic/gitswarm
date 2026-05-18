import type { Agent, FileEntry, Issue, PullRequest, PtyStreamResult, PtySession, Snapshot, Worktree } from '../types';

type JsonInit = RequestInit & { json?: unknown };

async function requestJson<T>(path: string, init: JsonInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  let body = init.body;
  if (init.json !== undefined) {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(init.json);
  }
  const res = await fetch(path, { ...init, headers, body });
  const text = await res.text();
  let parsed: unknown = null;
  if (text) {
    try {
      parsed = JSON.parse(text);
    } catch {
      parsed = text;
    }
  }
  if (!res.ok) {
    const message = typeof parsed === 'object' && parsed && 'error' in parsed ? String((parsed as { error: unknown }).error) : res.statusText;
    throw new Error(message || `request failed (${res.status})`);
  }
  return parsed as T;
}

async function requestText(path: string): Promise<string> {
  const res = await fetch(path);
  const text = await res.text();
  if (!res.ok) {
    try {
      const parsed = JSON.parse(text) as { error?: string };
      throw new Error(parsed.error || res.statusText);
    } catch {
      throw new Error(text || res.statusText);
    }
  }
  return text;
}

export async function fetchSnapshot(): Promise<Snapshot> {
  const [issues, prs, worktrees, files, ptys, agents] = await Promise.all([
    requestJson<{ issues: Issue[] }>('/api/issues'),
    requestJson<{ prs: PullRequest[] }>('/api/prs'),
    requestJson<{ worktrees: Worktree[] }>('/api/worktrees'),
    requestJson<{ files: FileEntry[] }>('/api/files'),
    requestJson<{ sessions: PtySession[] }>('/api/pty/list'),
    requestJson<{ agents: Agent[]; default: string; code_mtime: number }>('/api/agents'),
  ]);
  return {
    issues: issues.issues || [],
    prs: prs.prs || [],
    worktrees: worktrees.worktrees || [],
    files: files.files || [],
    ptys: ptys.sessions || [],
    agents: agents.agents || [],
    defaultAgent: agents.default || 'codex',
    codeMtime: agents.code_mtime || 0,
  };
}

export function fetchIssue(number: number) {
  return requestJson<Issue>(`/api/issue?num=${number}`);
}

export function fetchPrDiff(number: number) {
  return requestJson<{ number: number; diff: string }>(`/api/pr/diff?num=${number}`);
}

export function fetchFile(name: string, offset = 0) {
  return requestText(`/api/file?name=${encodeURIComponent(name)}&offset=${offset}`);
}

export function sendIssueLaunch(issue: number, agent: string, kind = 'issue-shell') {
  return requestJson('/api/pty/new', { method: 'POST', json: { kind, issue, agent } });
}

export function sendPromptLaunch(kind: string, payload: Record<string, unknown>) {
  return requestJson('/api/pty/new', { method: 'POST', json: { kind, ...payload } });
}

export function sendShellLaunch(agent: string, cwd = '') {
  return requestJson('/api/pty/new', { method: 'POST', json: { kind: 'agent-shell', agent, cwd } });
}

export function launchShell(cwd = '') {
  return requestJson('/api/pty/new', { method: 'POST', json: { kind: 'shell', cwd } });
}

export function updateIssue(issue: number, title?: string, body?: string) {
  return requestJson('/api/issue/update', { method: 'POST', json: { issue, title, body } });
}

export function createIssue(title: string, body = '') {
  return requestJson('/api/issue/create', { method: 'POST', json: { title, body } });
}

export function deleteIssue(issue: number) {
  return requestJson('/api/issue/delete', { method: 'POST', json: { issue } });
}

export function issueCleanup(staleDays = 7, dryRun = false) {
  return requestJson('/api/state/cleanup', { method: 'POST', json: { stale_days: staleDays, dry_run: dryRun } });
}

export function closePty(sid: string) {
  return requestJson('/api/pty/close', { method: 'POST', json: { sid } });
}

export function deletePty(sid: string) {
  return requestJson('/api/pty/delete', { method: 'POST', json: { sid } });
}

export function ptyInput(sid: string, data: string) {
  return requestJson('/api/pty/input', { method: 'POST', json: { sid, data } });
}

export function ptyResize(sid: string, rows: number, cols: number) {
  return requestJson('/api/pty/resize', { method: 'POST', json: { sid, rows, cols } });
}

export function removeWorktree(name: string) {
  return requestJson('/api/worktree/remove', { method: 'POST', json: { name } });
}

export async function readPtyStream(sid: string, offset: number, timeout = 15): Promise<PtyStreamResult> {
  const res = await fetch(`/api/pty/stream?sid=${encodeURIComponent(sid)}&offset=${offset}&timeout=${timeout}`);
  const text = await res.text();
  if (!res.ok) {
    try {
      const parsed = JSON.parse(text) as { error?: string };
      throw new Error(parsed.error || res.statusText);
    } catch {
      throw new Error(text || res.statusText);
    }
  }
  const nextOffset = Number(res.headers.get('X-Offset') || `${offset}`);
  return {
    text,
    offset: Number.isFinite(nextOffset) ? nextOffset : offset,
    alive: res.headers.get('X-Alive') === '1',
    drop: Number(res.headers.get('X-Drop') || '0'),
    reset: res.headers.get('X-Reset') === '1',
  };
}
