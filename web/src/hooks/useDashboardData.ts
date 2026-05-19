import { useEffect, useMemo, useRef, useState } from 'react';
import { fetchFile, fetchIssue, fetchPr, fetchPrDiff, fetchSnapshot } from '../api';
import type { Issue, Milestone, PullRequest, Snapshot } from '../types';
import type { ActivityItem, IssueFilter, Selection } from '../types/dashboard';

function loadPersistedSelection(): Selection {
  try {
    const raw = localStorage.getItem('gitswarm.selection');
    if (!raw) return { kind: 'none' };
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return { kind: 'none' };
    if (parsed.kind === 'issue' || parsed.kind === 'pr' || parsed.kind === 'milestone') {
      const id = Number(parsed.id);
      if (Number.isFinite(id)) return { kind: parsed.kind, id };
    }
    if (parsed.kind === 'pty' || parsed.kind === 'worktree' || parsed.kind === 'file') {
      if (typeof parsed.id === 'string' && parsed.id) return { kind: parsed.kind, id: parsed.id };
    }
  } catch {
    /* ignore */
  }
  return { kind: 'none' };
}

export function useDashboardData(issueFilter: IssueFilter) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selection, setSelection] = useState<Selection>(() => loadPersistedSelection());

  useEffect(() => {
    if (selection.kind === 'none') {
      localStorage.removeItem('gitswarm.selection');
    } else {
      localStorage.setItem('gitswarm.selection', JSON.stringify(selection));
    }
  }, [selection]);
  const [issueBody, setIssueBody] = useState('');
  const [issueDetail, setIssueDetail] = useState<Issue | null>(null);
  const [prDetail, setPrDetail] = useState<PullRequest | null>(null);
  const [prDiff, setPrDiff] = useState('');
  const [fileText, setFileText] = useState('');
  const loadTimer = useRef<number | null>(null);
  const loadSeq = useRef(0);
  const selectionRef = useRef(selection);
  const issuesRef = useRef<Issue[]>([]);
  const prsRef = useRef<PullRequest[]>([]);
  const hasAutoSelectedRef = useRef(selection.kind !== 'none');
  useEffect(() => {
    selectionRef.current = selection;
  }, [selection]);

  const issues = snapshot?.issues || [];
  const milestones = snapshot?.milestones || [];
  const prs = snapshot?.prs || [];
  const worktrees = snapshot?.worktrees || [];
  const files = snapshot?.files || [];
  const ptys = snapshot?.ptys || [];
  const agents = snapshot?.agents || [];
  const defaultAgent = snapshot?.defaultAgent || 'codex';
  issuesRef.current = issues;
  prsRef.current = prs;

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

  const selectedIssue = selection.kind === 'issue'
    ? (issueDetail?.number === selection.id ? issueDetail : issues.find((it) => it.number === selection.id) || null)
    : null;
  const selectedMilestone = selection.kind === 'milestone' ? milestones.find((it) => it.number === selection.id) || null : null;
  const selectedPr = selection.kind === 'pr'
    ? (prDetail?.number === selection.id ? prDetail : prs.find((it) => it.number === selection.id) || null)
    : null;
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
    const seq = ++loadSeq.current;
    try {
      const next = await fetchSnapshot();
      if (seq !== loadSeq.current) return;
      setSnapshot(next);
      if (!hasAutoSelectedRef.current && selectionRef.current.kind === 'none') {
        const firstIssue = next.issues.find((it) => Number.isFinite(it.number));
        const firstMilestone = next.milestones.find((it) => Number.isFinite(it.number));
        const firstPr = next.prs.find((it) => Number.isFinite(it.number));
        const firstPty = next.ptys.find((it) => !!it.sid);
        const firstWorktree = next.worktrees.find((it) => !!it.name);
        const firstFile = next.files.find((it) => !!it.name);
        if (firstIssue) setSelection({ kind: 'issue', id: firstIssue.number });
        else if (firstMilestone) setSelection({ kind: 'milestone', id: firstMilestone.number });
        else if (firstPr) setSelection({ kind: 'pr', id: firstPr.number });
        else if (firstPty) setSelection({ kind: 'pty', id: firstPty.sid });
        else if (firstWorktree) setSelection({ kind: 'worktree', id: firstWorktree.name });
        else if (firstFile) setSelection({ kind: 'file', id: firstFile.name });
        hasAutoSelectedRef.current = true;
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
    if (selection.kind === 'milestone' && !snapshot.milestones.some((x) => x.number === selection.id) && snapshot.milestones.length) {
      setSelection({ kind: 'milestone', id: snapshot.milestones[0].number });
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
    if (selection.kind === 'milestone' && milestones.length && !milestones.some((x) => x.number === selection.id)) {
      setSelection({ kind: 'milestone', id: milestones[0].number });
    }
  }, [milestones, selection]);

  // Fetch issue detail when the SELECTED issue changes — not on every snapshot
  // poll. Re-running on every `issues` change would clobber loaded comments
  // with the bare snapshot version every 4s, causing a visible flash.
  useEffect(() => {
    if (selection.kind !== 'issue' || !Number.isFinite(selection.id)) {
      setIssueDetail(null);
      return;
    }
    const targetId = selection.id;
    setIssueDetail((prev) => {
      if (prev?.number === targetId) return prev;
      const snapIssue = issuesRef.current.find((it) => it.number === targetId) || null;
      setIssueBody(snapIssue?.body || '');
      return snapIssue;
    });
    let cancelled = false;
    void fetchIssue(targetId)
      .then((detail) => {
        if (cancelled || selectionRef.current.kind !== 'issue' || selectionRef.current.id !== targetId) return;
        const snapIssue = issuesRef.current.find((it) => it.number === targetId) || null;
        setIssueDetail({ ...(snapIssue || detail), ...detail });
        setIssueBody(detail.body || '');
      })
      .catch((err) => {
        if (!cancelled) setIssueBody(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [selection.kind, selection.kind === 'issue' ? selection.id : null]);

  // Fetch PR detail + diff when the SELECTED pr changes — not on every poll.
  useEffect(() => {
    if (selection.kind !== 'pr' || !Number.isFinite(selection.id)) {
      setPrDetail(null);
      setPrDiff('');
      return;
    }
    const targetId = selection.id;
    setPrDetail((prev) => {
      if (prev?.number === targetId) return prev;
      const snapPr = prsRef.current.find((it) => it.number === targetId) || null;
      setPrDiff('');
      return snapPr;
    });
    let cancelled = false;
    void fetchPr(targetId)
      .then((detail) => {
        if (cancelled || selectionRef.current.kind !== 'pr' || selectionRef.current.id !== targetId) return;
        const snapPr = prsRef.current.find((it) => it.number === targetId) || null;
        setPrDetail({ ...(snapPr || detail), ...detail });
      })
      .catch(() => {
        /* keep the snapshot PR if detail fetch fails */
      });
    void fetchPrDiff(targetId)
      .then((data) => {
        if (cancelled || selectionRef.current.kind !== 'pr' || selectionRef.current.id !== targetId) return;
        setPrDiff(data.diff);
      })
      .catch((err) => {
        if (cancelled || selectionRef.current.kind !== 'pr' || selectionRef.current.id !== targetId) return;
        setPrDiff(err instanceof Error ? err.message : String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [selection.kind, selection.kind === 'pr' ? selection.id : null]);

  useEffect(() => {
    if (selection.kind === 'file') {
      const file = files.find((it) => it.name === selection.id);
      if (file) {
        void fetchFile(file.name).then(setFileText).catch((err) => setFileText(err instanceof Error ? err.message : String(err)));
      }
    }
  }, [selection, files]);

  const counts = useMemo(() => ({
    issues: issues.length,
    milestones: milestones.length,
    prs: prs.length,
    ptys: ptys.length,
    worktrees: worktrees.length,
    files: files.length,
  }), [issues.length, milestones.length, prs.length, ptys.length, worktrees.length, files.length]);

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
    milestones,
    prs,
    worktrees,
    files,
    ptys,
    agents,
    defaultAgent,
    visibleIssues,
    visibleClaimCount,
    selectedIssue,
    selectedMilestone,
    selectedPr,
    selectedPty,
    selectedWorktree,
    selectedFile,
    counts,
    recentActivity,
  };
}
