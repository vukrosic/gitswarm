import type { Issue, PullRequest, PtySession } from '../types';

export function issueLabel(issue: Issue): string {
  return `#${issue.number} · ${issue.title}`;
}

export function prLabel(pr: PullRequest): string {
  return `#${pr.number} · ${pr.title}`;
}

export function sessionLabel(p: PtySession): string {
  return p.label || p.sid;
}
