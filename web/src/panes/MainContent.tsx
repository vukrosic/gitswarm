import type { Agent, Issue, PullRequest, PtySession, Worktree, FileEntry, Snapshot } from '../types';
import type { Pane } from '../types/dashboard';
import { FilePane } from './FilePane';
import { IssuePane } from './IssuePane';
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
    <main className="main">
      {loading && !snapshot ? <div className="empty">Loading dashboard...</div> : null}
      {error ? <div className="error">{error}</div> : null}
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
