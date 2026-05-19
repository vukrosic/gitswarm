import { useEffect, useRef, useState } from 'react';
import {
  createIssue,
  deleteIssue,
  deletePty,
  closePty,
  launchAgentGrid,
  launchShell,
  ptyInput,
  removeWorktree,
  sendIssueLaunch,
  sendPromptLaunch,
  sendShellLaunch,
  updateIssue,
  issueCleanup,
  fetchNotifications,
} from './api';
import type { GitHubNotification, Issue, Milestone, PullRequest, PtySession, Worktree } from './types';
import type { IssueFilter, LaunchResult, Pane, Selection } from './types/dashboard';
import { AppHeader } from './components/AppHeader';
import { DashboardSidebar } from './components/DashboardSidebar';
import { TerminalDock } from './components/TerminalDock';
import { Button } from '@/components/ui/button';
import { MainContent } from './panes/MainContent';
import { AgentGridPane } from './panes/AgentGridPane';
import { useDashboardData } from './hooks/useDashboardData';
import { usePtyStream } from './hooks/usePtyStream';

function loadPersistedPane(): Pane {
  const value = localStorage.getItem('gitswarm.pane');
  if (value === 'issues' || value === 'prs' || value === 'pty' || value === 'worktrees' || value === 'files' || value === 'launch' || value === 'milestones' || value === 'agent-grid') {
    return value as Pane;
  }
  return 'issues';
}

export default function App() {
  const [pane, setPane] = useState<Pane>(() => loadPersistedPane());
  const [issueFilter, setIssueFilter] = useState<IssueFilter>('all');
  const dashboard = useDashboardData(issueFilter);
  const [launchText, setLaunchText] = useState('summarize the first 5 open issues');
  const [ptyText, setPtyText] = useState('');
  const [busy, setBusy] = useState<string>('');
  const [selectedAgent, setSelectedAgent] = useState(() => localStorage.getItem('gitswarm.agent') || 'codex');
  const [issueTitle, setIssueTitle] = useState('');
  const [issueDraftBody, setIssueDraftBody] = useState('');
  const [dockPtyId, setDockPtyId] = useState(() => localStorage.getItem('gitswarm.dockPtyId') || '');
  const [dockCollapsed, setDockCollapsed] = useState(() => localStorage.getItem('gitswarm.terminalDockCollapsed') === '1');
  const [notifications, setNotifications] = useState<GitHubNotification[]>([]);
  const [notifsLoading, setNotifsLoading] = useState(false);
  const codeMtimeRef = useRef(0);
  const {
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
    prependIssue,
  } = dashboard;
  const ptyStream = usePtyStream(selectedPty?.sid || '');
  const dockPty = dockPtyId
    ? ptys.find((it) => it.sid === dockPtyId) || {
        sid: dockPtyId,
        label: 'starting manual session...',
        cwd: '',
        alive: true,
        kind: 'shell',
      }
    : null;
  const manualPtys = ptys.filter((pty) => pty.kind === 'shell' || pty.kind === 'agent-shell');
  const dockStream = usePtyStream(dockPty?.sid || '');

  useEffect(() => {
    localStorage.setItem('gitswarm.agent', selectedAgent);
  }, [selectedAgent]);

  useEffect(() => {
    localStorage.setItem('gitswarm.terminalDockCollapsed', dockCollapsed ? '1' : '0');
  }, [dockCollapsed]);

  useEffect(() => {
    localStorage.setItem('gitswarm.pane', pane);
  }, [pane]);

  useEffect(() => {
    localStorage.setItem('gitswarm.dockPtyId', dockPtyId);
  }, [dockPtyId]);

  useEffect(() => {
    const codeMtime = snapshot?.codeMtime || 0;
    const codeMtimePath = snapshot?.codeMtimePath || '';
    if (!codeMtime) return;
    if (codeMtimeRef.current && codeMtime > codeMtimeRef.current + 0.5) {
      const delta = codeMtime - codeMtimeRef.current;
      // eslint-disable-next-line no-console
      console.warn(
        `[gitswarm] auto-reload triggered: ${codeMtimePath || '<unknown>'} ` +
          `changed (+${delta.toFixed(2)}s). prev=${codeMtimeRef.current.toFixed(2)} ` +
          `next=${codeMtime.toFixed(2)}`,
      );
      window.location.reload();
      return;
    }
    codeMtimeRef.current = codeMtime;
  }, [snapshot?.codeMtime, snapshot?.codeMtimePath]);

  useEffect(() => {
    if (!agents.length) return;
    if (!agents.some((agent) => agent.id === selectedAgent)) {
      setSelectedAgent(defaultAgent || agents[0].id);
    }
  }, [agents, defaultAgent, selectedAgent]);

  async function run<T>(label: string, fn: () => Promise<T>, reload = true) {
    setBusy(label);
    try {
      const res = await fn();
      if (reload) {
        await load();
      }
      return res;
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(`${label}: ${message}`);
      throw err;
    } finally {
      setBusy('');
    }
  }

  function shouldOpenInDock(pty: Pick<PtySession, 'kind'> | null | undefined) {
    return pty?.kind === 'shell' || pty?.kind === 'agent-shell';
  }

  const gridSessions = ptys.filter((p) => p.kind === 'agent-grid-cell') as unknown as import('./panes/AgentGridPane').GridSession[];
  const gridActive = gridSessions.length > 0;
  const gridLoading = false;

  async function handleLaunchGrid(agent: string, issueNumbers: number[], cols: number, rows: number) {
    await run('launch grid', async () => {
      const result = await launchAgentGrid(agent, issueNumbers, cols, rows);
      await load();
      return result;
    });
    setPane('agent-grid');
  }

  function focusMainPty(sid: string) {
    setPane('pty');
    setSelection({ kind: 'pty', id: sid });
  }

  function focusDockPty(sid: string) {
    setDockPtyId(sid);
    setDockCollapsed(false);
  }

  function focusPty(pty: PtySession) {
    if (shouldOpenInDock(pty)) {
      focusDockPty(pty.sid);
      return;
    }
    focusMainPty(pty.sid);
  }

  function focusLaunchResult(result: LaunchResult | undefined, target: 'main' | 'dock') {
    if (!result?.sid) return;
    if (target === 'dock') focusDockPty(result.sid);
    else focusMainPty(result.sid);
  }

  function focusIssue(issue: Issue) {
    setPane('issues');
    setSelection({ kind: 'issue', id: issue.number });
  }

  function openPrInGitHub(pr: PullRequest) {
    if (pr.url) {
      window.open(pr.url, '_blank', 'noopener,noreferrer');
    }
  }

  async function launchIssueShell(issue: Issue, focus = true) {
    const result = await run(`claim #${issue.number}`, async () => {
      return sendIssueLaunch(issue.number, selectedAgent, 'issue-shell') as Promise<LaunchResult>;
    });
    if (focus) {
      focusLaunchResult(result, 'main');
    }
    return result;
  }

  async function handleClaim(issue: Issue) {
    await launchIssueShell(issue, true);
  }

  async function launchIssueReview(issue: Issue, focus = true) {
    const result = await run(`review #${issue.number}`, async () => {
      return sendPromptLaunch('issue-review', { issue: issue.number, agent: selectedAgent }) as Promise<LaunchResult>;
    });
    if (focus) {
      focusLaunchResult(result, 'main');
    }
    return result;
  }

  async function handleReviewIssue(issue: Issue) {
    await launchIssueReview(issue, true);
  }

  async function handleFocusMilestoneIssue(issue: Issue) {
    focusIssue(issue);
  }

  async function handleOpenMilestoneIssues(milestone: Milestone) {
    const firstIssue = issues.find((issue) => issue.milestone?.number === milestone.number);
    if (firstIssue) {
      focusIssue(firstIssue);
      return;
    }
    if (visibleIssues.length) {
      focusIssue(visibleIssues[0]);
      return;
    }
    setPane('issues');
    setSelection({ kind: 'none' });
  }

  async function handleReviewPr(pr: PullRequest) {
    const result = await run(`review PR #${pr.number}`, async () => {
      return sendPromptLaunch('pr-review', { pr: pr.number, agent: selectedAgent }) as Promise<LaunchResult>;
    });
    focusLaunchResult(result, 'main');
  }

  async function handleMergePr(pr: PullRequest) {
    const result = await run(`merge PR #${pr.number}`, async () => {
      return sendPromptLaunch('merge-pr', { pr: pr.number, agent: selectedAgent }) as Promise<LaunchResult>;
    });
    focusLaunchResult(result, 'main');
  }

  async function handleFixCi(pr: PullRequest) {
    const result = await run(`fix-ci PR #${pr.number}`, async () => {
      return sendPromptLaunch('ci-fix', { pr: pr.number, agent: selectedAgent }) as Promise<LaunchResult>;
    });
    focusLaunchResult(result, 'main');
  }

  async function handlePropose() {
    const result = await run('propose', async () => {
      return sendPromptLaunch('propose-issue', { agent: selectedAgent, slug: launchText }) as Promise<LaunchResult>;
    });
    focusLaunchResult(result, 'main');
  }

  async function handleNewShell() {
    const result = await run('shell', async () => {
      return launchShell() as Promise<LaunchResult>;
    });
    focusLaunchResult(result, 'dock');
  }

  async function handleAgentShell() {
    const result = await run('agent-shell', async () => {
      return sendShellLaunch(selectedAgent) as Promise<LaunchResult>;
    });
    focusLaunchResult(result, 'dock');
  }

  async function handleDeleteIssue(issue: Issue) {
    if (!confirm(`Delete issue #${issue.number}?`)) return;
    await run(`delete #${issue.number}`, async () => {
      await deleteIssue(issue.number);
    });
  }

  async function handleEditIssue(issue: Issue) {
    await run(`update #${issue.number}`, async () => {
      await updateIssue(issue.number, issue.title, issueBody);
    });
  }

  async function handleDeletePty(p: PtySession) {
    if (!confirm(`Delete session ${p.label}?`)) return;
    await run(`delete pty ${p.sid}`, async () => {
      await deletePty(p.sid);
    });
    if (dockPtyId === p.sid) {
      setDockPtyId('');
    }
    if (selection.kind === 'pty' && selection.id === p.sid) {
      setSelection({ kind: 'none' });
    }
  }

  async function handleClosePty(p: PtySession) {
    await run(`close pty ${p.sid}`, async () => {
      await closePty(p.sid);
    });
  }

  async function handleSendPty() {
    if (selection.kind !== 'pty') return;
    await run('send pty', async () => {
      await ptyInput(selection.id, ptyText.endsWith('\n') ? ptyText : `${ptyText}\n`);
      setPtyText('');
    }, false);
  }

  async function handlePtyCtrlC() {
    if (selection.kind !== 'pty') return;
    await run('ctrl-c pty', async () => {
      await ptyInput(selection.id, '\u0003');
    }, false);
  }

  async function handleDockType(value: string) {
    if (!dockPtyId) return;
    await ptyInput(dockPtyId, value);
  }

  async function handleDockClose() {
    if (!dockPty) return;
    await handleClosePty(dockPty);
  }

  async function handleDockDelete() {
    if (!dockPty) return;
    await handleDeletePty(dockPty);
  }

  async function handleWorktreeRemove(w: Worktree) {
    if (!confirm(`Remove worktree ${w.name}?`)) return;
    await run(`remove ${w.name}`, async () => {
      await removeWorktree(w.name);
    });
  }

  async function handleWorktreeShell(w: Worktree) {
    const result = await run(`shell ${w.name}`, async () => {
      return launchShell(w.path || `.agent-worktrees/${w.name}`) as Promise<LaunchResult>;
    });
    focusLaunchResult(result, 'dock');
  }

  async function handleCleanup(dryRun: boolean) {
    const label = dryRun ? 'cleanup audit' : 'cleanup prune';
    await run(label, async () => {
      await issueCleanup(7, dryRun);
    });
  }

  async function handlePruneMergedWorktrees() {
    const targets = worktrees.filter((worktree) => worktree.safe_remove && !worktree.running);
    if (!targets.length) return;
    if (!confirm(`Prune ${targets.length} merged worktree${targets.length === 1 ? '' : 's'}?`)) return;
    await run('prune merged worktrees', async () => {
      for (const worktree of targets) {
        await removeWorktree(worktree.name);
      }
    });
  }

  async function handleCreateIssue() {
    const title = issueTitle.trim();
    if (!title) return;
    const body = issueDraftBody;
    const result = await run('create issue', async () => {
      return createIssue(title, issueDraftBody) as Promise<{ number?: number; url?: string }>;
    }, false);
    if (result && typeof result === 'object' && result.number) {
      const createdAt = new Date().toISOString();
      prependIssue({
        number: result.number,
        title,
        body,
        state: 'open',
        assignees: [],
        created_at: createdAt,
        updated_at: createdAt,
        in_progress: false,
        labels: [],
        comment_count: 0,
        comments: [],
        milestone: null,
        url: result.url || undefined,
      });
      setPane('issues');
      setIssueTitle('');
      setIssueDraftBody('');
      setSelection({ kind: 'issue', id: result.number });
      void load();
    }
  }

  function handleOpenIssueCreator() {
    setPane('launch');
  }

  async function handleBatchReviewVisible() {
    const batch = visibleIssues.slice(0, 10);
    if (!batch.length) return;
    if (!confirm(`Launch ${batch.length} visible issue review${batch.length === 1 ? '' : 's'}?`)) return;
    for (let i = 0; i < batch.length; i += 1) {
      await launchIssueReview(batch[i], false);
      if (i < batch.length - 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 750));
      }
    }
    await load();
  }

  async function handleRefreshNotifications() {
    setNotifsLoading(true);
    try {
      const res = await fetchNotifications();
      setNotifications(res.notifications || []);
    } catch {
      // silently ignore
    } finally {
      setNotifsLoading(false);
    }
  }

  async function handleBatchClaimNext() {
    const batch = issues.filter((issue) => issue.claim_next && !issue.in_progress).slice(0, 3);
    if (!batch.length) return;
    if (!confirm(`Launch ${batch.length} claim-next issue${batch.length === 1 ? '' : 's'}?`)) return;
    for (let i = 0; i < batch.length; i += 1) {
      await launchIssueShell(batch[i], i === batch.length - 1);
      if (i < batch.length - 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 800));
      }
    }
  }

  const selectedIssueActions = selectedIssue ? (
    <>
      <Button
        variant="outline"
        size="sm"
        onClick={() => void handleReviewIssue(selectedIssue)}
        loading={busy === `review #${selectedIssue.number}`}
        disabled={!!busy}
      >
        Review issue
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={() => void launchIssueShell(selectedIssue)}
        loading={busy === `claim #${selectedIssue.number}`}
        disabled={!!busy}
      >
        Open terminal
      </Button>
    </>
  ) : null;

  const sidebarToolbar = (() => {
    switch (pane) {
      case 'issues':
        return (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleBatchReviewVisible()}
              loading={busy === 'batch review' || busy.startsWith('review #')}
              disabled={!!busy}
            >
              Batch review
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleBatchClaimNext()}
              loading={busy === 'batch claim-next' || busy.startsWith('claim #')}
              disabled={!!busy}
            >
              Batch claim-next
            </Button>
            <Button variant="outline" size="sm" onClick={() => handleOpenIssueCreator()} disabled={!!busy}>
              New issue
            </Button>
            {selectedIssueActions}
          </>
        );
      case 'milestones':
        return (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void (selectedMilestone ? handleOpenMilestoneIssues(selectedMilestone) : undefined)}
              disabled={!!busy}
            >
              Open issues
            </Button>
            {selectedMilestone?.url ? (
              <Button variant="outline" size="sm" onClick={() => window.open(selectedMilestone.url, '_blank', 'noopener,noreferrer')} disabled={!!busy}>
                GitHub
              </Button>
            ) : null}
          </>
        );
      case 'pty':
        return (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleNewShell()}
              loading={busy === 'shell'}
              disabled={!!busy}
            >
              New shell
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleAgentShell()}
              loading={busy === 'agent-shell'}
              disabled={!!busy}
            >
              Agent shell
            </Button>
            {selectedPty ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handleSendPty()}
                  loading={busy === 'send pty'}
                  disabled={!!busy}
                >
                  Send
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handlePtyCtrlC()}
                  loading={busy === 'ctrl-c pty'}
                  disabled={!!busy}
                >
                  Ctrl-C
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handleClosePty(selectedPty)}
                  loading={busy === `close pty ${selectedPty.sid}`}
                  disabled={!!busy}
                >
                  Close
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => void handleDeletePty(selectedPty)}
                  loading={busy === `delete pty ${selectedPty.sid}`}
                  disabled={!!busy}
                >
                  Delete
                </Button>
              </>
            ) : null}
          </>
        );
      case 'worktrees':
        return (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handlePruneMergedWorktrees()}
              loading={busy === 'prune merged worktrees'}
              disabled={!!busy}
            >
              Prune merged
            </Button>
            {selectedWorktree ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => void handleWorktreeShell(selectedWorktree)}
                  loading={busy === `shell ${selectedWorktree.name}`}
                  disabled={!!busy}
                >
                  Shell
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => void handleWorktreeRemove(selectedWorktree)}
                  loading={busy === `remove ${selectedWorktree.name}`}
                  disabled={!!busy}
                >
                  Remove
                </Button>
              </>
            ) : null}
          </>
        );
      case 'launch':
        return (
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleCleanup(true)}
              loading={busy === 'cleanup audit'}
              disabled={!!busy}
            >
              Audit cleanup
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleCleanup(false)}
              loading={busy === 'cleanup prune'}
              disabled={!!busy}
            >
              Prune cleanup
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => void handleCreateIssue()}
              loading={busy === 'create issue'}
              disabled={!!busy}
            >
              Create issue
            </Button>
          </>
        );
      default:
        return null;
    }
  })();

  return (
    <div className="relative flex h-full min-h-0 flex-col overflow-hidden">
      <AppHeader
        agents={agents}
        defaultAgent={defaultAgent}
        selectedAgent={selectedAgent}
        busy={busy}
        dockCollapsed={dockCollapsed}
        onAgentChange={setSelectedAgent}
        onNewShell={() => void handleNewShell()}
        onNewAgent={() => void handleAgentShell()}
        onRefresh={() => void run('refresh dashboard', async () => {
          await load();
        }, false)}
        onToggleDock={() => setDockCollapsed((value) => !value)}
      />

      <div
        className={`relative grid min-h-0 flex-1 gap-4 overflow-hidden p-4 ${
          dockCollapsed
            ? 'lg:grid-cols-[340px_minmax(0,1fr)]'
            : 'lg:grid-cols-[340px_minmax(340px,0.95fr)_minmax(420px,1.25fr)]'
        } max-lg:grid-cols-[280px_minmax(0,1fr)] max-lg:grid-rows-[1fr_minmax(380px,54vh)] max-md:grid-cols-1 max-md:grid-rows-[auto_auto_minmax(300px,50vh)]`}
      >
        <DashboardSidebar
          pane={pane}
          counts={counts}
          visibleIssues={visibleIssues}
          issueFilter={issueFilter}
          selection={selection}
          milestones={milestones}
          prs={prs}
          ptys={ptys}
          worktrees={worktrees}
          files={files}
          agents={agents}
          selectedAgent={selectedAgent}
          busy={busy}
          toolbar={sidebarToolbar}
          onPaneChange={setPane}
          onIssueFilterChange={setIssueFilter}
          onSelect={setSelection}
          onFocusPty={focusPty}
          onSelectAgent={setSelectedAgent}
          onClaimIssue={(issue) => void handleClaim(issue)}
          onReviewIssue={(issue) => void handleReviewIssue(issue)}
          onIssueTerminal={(issue) => void launchIssueShell(issue)}
          onSelectMilestoneIssue={(milestone) => void handleOpenMilestoneIssues(milestone)}
          onReviewPr={(pr) => void handleReviewPr(pr)}
          onMergePr={(pr) => void handleMergePr(pr)}
          onFixCi={(pr) => void handleFixCi(pr)}
          onClosePty={(pty) => void handleClosePty(pty)}
          onDeletePty={(pty) => void handleDeletePty(pty)}
          onWorktreeShell={(worktree) => void handleWorktreeShell(worktree)}
          onWorktreeRemove={(worktree) => void handleWorktreeRemove(worktree)}
        />

        {pane === 'agent-grid' ? (
          <AgentGridPane
            agents={agents}
            selectedAgent={selectedAgent}
            onAgentChange={setSelectedAgent}
            onLaunch={handleLaunchGrid}
            onFocusSession={focusMainPty}
            gridSessions={gridSessions}
            loading={gridLoading}
          />
        ) : (
        <MainContent
          pane={pane}
          loading={loading}
          busy={busy}
          snapshot={snapshot}
          error={error}
          selectedIssue={selectedIssue}
          selectedMilestone={selectedMilestone}
          selectedPr={selectedPr}
          selectedPty={selectedPty}
          selectedWorktree={selectedWorktree}
          selectedFile={selectedFile}
          issueBody={issueBody}
          prDiff={prDiff}
          fileText={fileText}
          ptyText={ptyText}
          ptyStream={ptyStream}
          selectedAgent={selectedAgent}
          issueTitle={issueTitle}
          issueDraftBody={issueDraftBody}
          launchText={launchText}
          onIssueBodyChange={setIssueBody}
          onPtyTextChange={setPtyText}
          onIssueTitleChange={setIssueTitle}
          onIssueDraftBodyChange={setIssueDraftBody}
          onLaunchTextChange={setLaunchText}
          onOpenIssueCreator={() => handleOpenIssueCreator()}
          onCreateIssue={() => void handleCreateIssue()}
          onClaimIssue={(issue) => void handleClaim(issue)}
          onReviewIssue={(issue) => void handleReviewIssue(issue)}
          onSaveIssue={(issue) => void handleEditIssue(issue)}
          onDeleteIssue={(issue) => void handleDeleteIssue(issue)}
          onFocusMilestoneIssue={(issue) => void handleFocusMilestoneIssue(issue)}
          onOpenPrGitHub={(pr) => void openPrInGitHub(pr)}
          onReviewPr={(pr) => void handleReviewPr(pr)}
          onMergePr={(pr) => void handleMergePr(pr)}
          onFixCi={(pr) => void handleFixCi(pr)}
          onSendPty={() => void handleSendPty()}
          onPtyCtrlC={() => void handlePtyCtrlC()}
          onClosePty={(pty) => void handleClosePty(pty)}
          onDeletePty={(pty) => void handleDeletePty(pty)}
          onWorktreeShell={(worktree) => void handleWorktreeShell(worktree)}
          onWorktreeRemove={(worktree) => void handleWorktreeRemove(worktree)}
          onPropose={() => void handlePropose()}
          onAuditCleanup={() => void handleCleanup(true)}
          onPruneCleanup={() => void handleCleanup(false)}
          onBatchReview={() => void handleBatchReviewVisible()}
          onBatchClaimNext={() => void handleBatchClaimNext()}
          onPruneMerged={() => void handlePruneMergedWorktrees()}
          notifications={notifications}
          notificationsLoading={notifsLoading}
          onRefreshNotifications={() => void handleRefreshNotifications()}
        />
        )}

        {!dockCollapsed ? (
          <div className="grid min-h-0 gap-3 overflow-hidden max-lg:col-span-full max-lg:grid-cols-[minmax(360px,1.2fr)_minmax(260px,0.8fr)] max-md:grid-cols-1">
            <TerminalDock
              pty={dockPty}
              sessions={manualPtys}
              log={dockStream.text}
              offset={dockStream.offset}
              alive={dockStream.alive}
              collapsed={dockCollapsed}
              busy={busy}
              onClose={() => void handleDockClose()}
              onDelete={() => void handleDockDelete()}
              onToggle={() => setDockCollapsed((value) => !value)}
              onNewAgent={() => void handleAgentShell()}
              onFocusSession={focusPty}
              onType={(value) => void handleDockType(value)}
            />
          </div>
        ) : null}
      </div>
    </div>
  );
}
