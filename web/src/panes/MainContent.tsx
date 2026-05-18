import type { Agent, FileEntry, Issue, Milestone, PullRequest, PtySession, Snapshot, Worktree } from '../types';
import type { Pane } from '../types/dashboard';
import { FilePane } from './FilePane';
import { IssuePane } from './IssuePane';
import { MilestonePane } from './MilestonePane';
import { LaunchPane } from './LaunchPane';
import { PrPane } from './PrPane';
import { TerminalPane } from './TerminalPane';
import { WorktreePane } from './WorktreePane';

interface PtyStreamState {
  text: string;
  offset: number;
  alive: boolean;
}

interface MainContentProps {
  pane: Pane;
  loading: boolean;
  snapshot: Snapshot | null;
  error: string;
  selectedIssue: Issue | null;
  selectedMilestone: Milestone | null;
  selectedPr: PullRequest | null;
  selectedPty: PtySession | null;
  selectedWorktree: Worktree | null;
  selectedFile: FileEntry | null;
  issueBody: string;
  prDiff: string;
  fileText: string;
  ptyText: string;
  ptyStream: PtyStreamState;
  agents: Agent[];
  selectedAgent: string;
  issueTitle: string;
  issueDraftBody: string;
  launchText: string;
  onIssueBodyChange: (value: string) => void;
  onPtyTextChange: (value: string) => void;
  onIssueTitleChange: (value: string) => void;
  onIssueDraftBodyChange: (value: string) => void;
  onLaunchTextChange: (value: string) => void;
  onClaimIssue: (issue: Issue) => void;
  onReviewIssue: (issue: Issue) => void;
  onSaveIssue: (issue: Issue) => void;
  onDeleteIssue: (issue: Issue) => void;
  onFocusMilestoneIssue: (issue: Issue) => void;
  onReviewPr: (pr: PullRequest) => void;
  onMergePr: (pr: PullRequest) => void;
  onFixCi: (pr: PullRequest) => void;
  onSendPty: () => void;
  onPtyCtrlC: () => void;
  onClosePty: (pty: PtySession) => void;
  onDeletePty: (pty: PtySession) => void;
  onWorktreeShell: (worktree: Worktree) => void;
  onWorktreeRemove: (worktree: Worktree) => void;
  onNewShell: () => void;
  onAgentShell: () => void;
  onPropose: () => void;
  onAuditCleanup: () => void;
  onPruneCleanup: () => void;
  onCreateIssue: () => void;
  onBatchReview: () => void;
  onBatchClaimNext: () => void;
  onPruneMerged: () => void;
}

export function MainContent(props: MainContentProps) {
  const {
    pane,
    loading,
    snapshot,
    error,
    selectedIssue,
    selectedMilestone,
    selectedPr,
    selectedPty,
    selectedWorktree,
    selectedFile,
    issueBody,
    prDiff,
    fileText,
    ptyText,
    ptyStream,
    agents,
    selectedAgent,
    issueTitle,
    issueDraftBody,
    launchText,
    onIssueBodyChange,
    onPtyTextChange,
    onIssueTitleChange,
    onIssueDraftBodyChange,
    onLaunchTextChange,
    onClaimIssue,
    onReviewIssue,
    onSaveIssue,
    onDeleteIssue,
    onFocusMilestoneIssue,
    onReviewPr,
    onMergePr,
    onFixCi,
    onSendPty,
    onPtyCtrlC,
    onClosePty,
    onDeletePty,
    onWorktreeShell,
    onWorktreeRemove,
    onNewShell,
    onAgentShell,
    onPropose,
    onAuditCleanup,
    onPruneCleanup,
    onCreateIssue,
    onBatchReview,
    onBatchClaimNext,
    onPruneMerged,
  } = props;

  return (
    <main className="scrollbar-thin min-h-0 min-w-0 overflow-y-auto overflow-x-hidden">
      {loading && !snapshot ? (
        <div className="rounded-[var(--radius)] border border-border bg-card/60 px-5 py-4 text-sm text-muted-foreground">
          Loading dashboard...
        </div>
      ) : null}
      {error ? (
        <div className="rounded-[var(--radius)] border border-destructive/40 bg-destructive/10 px-5 py-4 text-sm text-destructive">
          {error}
        </div>
      ) : null}
      {pane === 'issues' && selectedIssue ? (
        <IssuePane
          issue={selectedIssue}
          body={issueBody}
          onBodyChange={onIssueBodyChange}
          onClaim={() => onClaimIssue(selectedIssue)}
          onReview={() => onReviewIssue(selectedIssue)}
          onSave={() => onSaveIssue(selectedIssue)}
          onDelete={() => onDeleteIssue(selectedIssue)}
        />
      ) : null}
      {pane === 'milestones' && selectedMilestone ? (
        <MilestonePane
          milestone={selectedMilestone}
          issues={snapshot?.issues || []}
          onFocusIssue={onFocusMilestoneIssue}
          onOpenGitHub={() => {
            if (selectedMilestone.url) window.open(selectedMilestone.url, '_blank', 'noopener,noreferrer');
          }}
        />
      ) : null}
      {pane === 'prs' && selectedPr ? (
        <PrPane
          pr={selectedPr}
          diff={prDiff}
          onReview={() => onReviewPr(selectedPr)}
          onMerge={() => onMergePr(selectedPr)}
          onFixCi={() => onFixCi(selectedPr)}
        />
      ) : null}
      {pane === 'pty' && selectedPty ? (
        <TerminalPane
          pty={selectedPty}
          input={ptyText}
          log={ptyStream.text}
          offset={ptyStream.offset}
          alive={ptyStream.alive}
          onInputChange={onPtyTextChange}
          onSend={onSendPty}
          onCtrlC={onPtyCtrlC}
          onClose={() => onClosePty(selectedPty)}
          onDelete={() => onDeletePty(selectedPty)}
        />
      ) : null}
      {pane === 'worktrees' && selectedWorktree ? (
        <WorktreePane
          worktree={selectedWorktree}
          onShell={() => onWorktreeShell(selectedWorktree)}
          onRemove={() => onWorktreeRemove(selectedWorktree)}
        />
      ) : null}
      {pane === 'files' && selectedFile ? <FilePane file={selectedFile} text={fileText} /> : null}
      {pane === 'launch' ? (
        <LaunchPane
          agents={agents}
          selectedAgent={selectedAgent}
          issueTitle={issueTitle}
          issueBody={issueDraftBody}
          launchText={launchText}
          onIssueTitleChange={onIssueTitleChange}
          onIssueBodyChange={onIssueDraftBodyChange}
          onLaunchTextChange={onLaunchTextChange}
          onNewShell={onNewShell}
          onAgentShell={onAgentShell}
          onPropose={onPropose}
          onAuditCleanup={onAuditCleanup}
          onPruneCleanup={onPruneCleanup}
          onCreateIssue={onCreateIssue}
          onBatchReview={onBatchReview}
          onBatchClaimNext={onBatchClaimNext}
          onPruneMerged={onPruneMerged}
        />
      ) : null}
    </main>
  );
}
