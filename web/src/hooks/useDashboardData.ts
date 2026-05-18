import { useEffect, useMemo, useRef, useState } from 'react';
import { fetchFile, fetchPrDiff, fetchSnapshot } from '../api';
import type { Issue, Snapshot } from '../types';
import type { ActivityItem, IssueFilter, Selection } from '../types/dashboard';

export function useDashboardData(issueFilter: IssueFilter) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState<Selection>({ kind: 'none' });
  const [issueBody, setIssueBody] = useState('');
  const [issueDetail, setIssueDetail] = useState<Issue | null>(null);
  const [prDiff, setPrDiff] = useState('');
  const [fileText, setFileText] = useState('');
  const loadTimer = useRef<number | null>(null);

  const issues = snapshot?.issues || [];
  const prs = snapshot?.prs || [];
  const worktrees = snapshot?.worktrees || [];
  const files = snapshot?.files || [];
  const ptys = snapshot?.ptys || [];
  const agents = snapshot?.agents || [];
  const defaultAgent = snapshot?.defaultAgent || 'codex';

  const visibleIssues = useMemo(() => {
    if (issueFilter === 'all') return issues;
    return issues.filter((issue) => {
      if (issueFilter === 'parked') return !!issue.parked;
      if (issueFilter === 'claim-next') return !!issue.claim_next;
      return (issue.labels || []).includes(issueFilter);
    });
  }, [issues, issueFilter]);

  const visibleClaimCount = useMemo(
    () => visibleIssues.filter((issue) => issue.claim_next && !issue.in_progress).length,
    [visibleIssues],
  );

  const selectedIssue = selection.kind === 'issue' ? issueDetail || issues.find((it) => it.number === selection.id) || null : null;
  const selectedPr = selection.kind === 'pr' ? prs.find((it) => it.number === selection.id) || null : null;
  const selectedPty = selection.kind === 'pty'
    ? ptys.find((it) => it.sid === selection.id) || {
        sid: selection.id,
        label: 'starting session...',
        cwd: '',
        alive: true,
      }
    : null;
  const selectedWorktree = selection.kind === 'worktree' ? worktrees.find((it) => it.name === selection.id) || null : null;
  const selectedFile = selection.kind === 'file' ? files.find((it) => it.name === selection.id) || null : null;

  async function load() {
    try {
      const next = await fetchSnapshot();
      setSnapshot(next);
      if (selection.kind === 'none') {
        if (visibleIssues.length) setSelection({ kind: 'issue', id: visibleIssues[0].number });
        else if (next.issues.length) setSelection({ kind: 'issue', id: next.issues[0].number });
        else if (next.prs.length) setSelection({ kind: 'pr', id: next.prs[0].number });
        else if (next.ptys.length) setSelection({ kind: 'pty', id: next.ptys[0].sid });
        else if (next.worktrees.length) setSelection({ kind: 'worktree', id: next.worktrees[0].name });
        else if (next.files.length) setSelection({ kind: 'file', id: next.files[0].name });
      }
      setError('');
      setLoading(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setLoading(false);
    }
  }

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      if (!alive) return;
      await load();
      if (!alive) return;
      loadTimer.current = window.setTimeout(tick, 4000);
    };
    void tick();
    return () => {
      alive = false;
      if (loadTimer.current) window.clearTimeout(loadTimer.current);
    };
  }, []);

  useEffect(() => {
    if (!snapshot) return;
    if (selection.kind === 'issue' && !snapshot.issues.some((x) => x.number === selection.id) && snapshot.issues.length) {
      setSelection({ kind: 'issue', id: snapshot.issues[0].number });
    }
    if (selection.kind === 'pr' && !snapshot.prs.some((x) => x.number === selection.id) && snapshot.prs.length) {
      setSelection({ kind: 'pr', id: snapshot.prs[0].number });
    }
    if (selection.kind === 'pty' && !snapshot.ptys.some((x) => x.sid === selection.id) && snapshot.ptys.length) {
      setSelection({ kind: 'pty', id: snapshot.ptys[0].sid });
    }
    if (selection.kind === 'worktree' && !snapshot.worktrees.some((x) => x.name === selection.id) && snapshot.worktrees.length) {
      setSelection({ kind: 'worktree', id: snapshot.worktrees[0].name });
    }
    if (selection.kind === 'file' && !snapshot.files.some((x) => x.name === selection.id) && snapshot.files.length) {
      setSelection({ kind: 'file', id: snapshot.files[0].name });
    }
  }, [snapshot, selection]);

  useEffect(() => {
    if (selection.kind === 'issue' && visibleIssues.length && !visibleIssues.some((x) => x.number === selection.id)) {
      setSelection({ kind: 'issue', id: visibleIssues[0].number });
    }
  }, [issueFilter, selection, visibleIssues]);

  useEffect(() => {
    if (selection.kind === 'issue') {
      const issue = issues.find((it) => it.number === selection.id) || null;
      setIssueDetail(issue);
      setIssueBody(issue?.body || '');
    }
    if (selection.kind === 'pr') {
      const pr = prs.find((it) => it.number === selection.id);
      if (pr) {
        void fetchPrDiff(pr.number).then((data) => setPrDiff(data.diff)).catch((err) => setPrDiff(err instanceof Error ? err.message : String(err)));
      }
    }
    if (selection.kind === 'file') {
      const file = files.find((it) => it.name === selection.id);
      if (file) {
        void fetchFile(file.name).then(setFileText).catch((err) => setFileText(err instanceof Error ? err.message : String(err)));
      }
    }
  }, [selection, issues, prs, files]);

  const counts = useMemo(() => ({
    issues: issues.length,
    prs: prs.length,
    ptys: ptys.length,
    worktrees: worktrees.length,
    files: files.length,
  }), [issues.length, prs.length, ptys.length, worktrees.length, files.length]);

  const recentActivity = useMemo(() => {
    const items: ActivityItem[] = [];
    for (const issue of issues) {
      const ts = Date.parse(issue.updated_at);
      if (Number.isFinite(ts)) {
        items.push({
          kind: 'issue',
          title: `#${issue.number} ${issue.title}`,
          meta: issue.summary || issue.state,
          ts,
          id: String(issue.number),
        });
      }
    }
    for (const pr of prs) {
      const ts = Date.parse((pr as typeof pr & { updatedAt?: string }).updatedAt || '');
      if (Number.isFinite(ts)) {
        items.push({
          kind: 'pr',
          title: `PR #${pr.number} ${pr.title}`,
          meta: pr.summary || pr.ci || pr.state,
          ts,
          id: String(pr.number),
        });
      }
    }
    for (const pty of ptys) {
      const ts = (pty.last_output || pty.started || 0) * 1000;
      if (ts > 0) {
        items.push({
          kind: 'pty',
          title: pty.label || pty.sid,
          meta: pty.cwd || pty.kind || 'pty',
          ts,
          id: pty.sid,
        });
      }
    }
    return items.sort((a, b) => b.ts - a.ts).slice(0, 8);
  }, [issues, prs, ptys]);

  return {
    snapshot,
    loading,
    error,
    setError,
    load,
    selection,
    setSelection,
    issueBody,
    setIssueBody,
    prDiff,
    fileText,
    issues,
    prs,
    worktrees,
    files,
    ptys,
    agents,
    defaultAgent,
    visibleIssues,
    visibleClaimCount,
    selectedIssue,
    selectedPr,
    selectedPty,
    selectedWorktree,
    selectedFile,
    counts,
    recentActivity,
  };
}
