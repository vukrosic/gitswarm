import type { FileEntry, GitHubNotification, Issue, Milestone, PullRequest, PtySession, Snapshot, Worktree } from '../types';
import type { Pane } from '../types/dashboard';
import { FilePane } from './FilePane';
import { IssuePane } from './IssuePane';
import { MilestonePane } from './MilestonePane';
import { LaunchPane } from './LaunchPane';
import { NotificationsPane } from './NotificationsPane';
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
  busy: string;
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
  ptyStream: PtyStreamState;
  selectedAgent: string;
  issueTitle: string;
  issueDraftBody: string;
  launchText: string;
  notifications: GitHubNotification[];
  onIssueBodyChange: (value: string) => void;
  onIssueTitleChange: (value: string) => void;
  onIssueDraftBodyChange: (value: string) => void;
  onLaunchTextChange: (value: string) => void;
  onOpenIssueCreator: () => void;
  onCreateIssue: () => void;
  onClaimIssue: (issue: Issue) => void;
  onReviewIssue: (issue: Issue) => void;
  onSaveIssue: (issue: Issue) => void;
  onDeleteIssue: (issue: Issue) => void;
  onFocusMilestoneIssue: (issue: Issue) => void;
  onOpenPrGitHub: (pr: PullRequest) => void;
  onReviewPr: (pr: PullRequest) => void;
  onMergePr: (pr: PullRequest) => void;
  onFixCi: (pr: PullRequest) => void;
  onTypePty: (value: string) => void;
  onClosePty: (pty: PtySession) => void;
  onDeletePty: (pty: PtySession) => void;
  onWorktreeShell: (worktree: Worktree) => void;
  onWorktreeRemove: (worktree: Worktree) => void;
  onPropose: () => void;
  onAuditCleanup: () => void;
  onPruneCleanup: () => void;
  onBatchReview: () => void;
  onBatchClaimNext: () => void;
  onPruneMerged: () => void;
  onRefreshNotifications: () => void;
  notificationsLoading: boolean;
}

export function MainContent(props: MainContentProps) {
  const {
    pane,
    loading,
    busy,
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
    ptyStream,
    selectedAgent,
    issueTitle,
    issueDraftBody,
    launchText,
    notifications,
    onRefreshNotifications,
    onIssueBodyChange,
    onIssueTitleChange,
    onIssueDraftBodyChange,
    onLaunchTextChange,
    onOpenIssueCreator,
    onCreateIssue,
    onClaimIssue,
    onReviewIssue,
    onSaveIssue,
    onDeleteIssue,
    onFocusMilestoneIssue,
    onOpenPrGitHub,
    onReviewPr,
    onMergePr,
    onFixCi,
    onTypePty,
    onClosePty,
    onDeletePty,
    onWorktreeShell,
    onWorktreeRemove,
    onPropose,
    onAuditCleanup,
    onPruneCleanup,
    onBatchReview,
    onBatchClaimNext,
    onPruneMerged,
    notificationsLoading,
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
          busy={busy}
          onBodyChange={onIssueBodyChange}
          onOpenIssueCreator={onOpenIssueCreator}
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
          onOpenGitHub={() => onOpenPrGitHub(selectedPr)}
          busy={busy}
          onReview={() => onReviewPr(selectedPr)}
          onMerge={() => onMergePr(selectedPr)}
          onFixCi={() => onFixCi(selectedPr)}
        />
      ) : null}
      {pane === 'pty' && selectedPty ? (
        <TerminalPane
          pty={selectedPty}
          log={ptyStream.text}
          offset={ptyStream.offset}
          alive={ptyStream.alive}
          busy={busy}
          onType={onTypePty}
          onClose={() => onClosePty(selectedPty)}
          onDelete={() => onDeletePty(selectedPty)}
        />
      ) : null}
      {pane === 'worktrees' && selectedWorktree ? (
        <WorktreePane
          worktree={selectedWorktree}
          busy={busy}
          onShell={() => onWorktreeShell(selectedWorktree)}
          onRemove={() => onWorktreeRemove(selectedWorktree)}
        />
      ) : null}
      {pane === 'files' && selectedFile ? <FilePane file={selectedFile} text={fileText} /> : null}
      {pane === 'launch' ? (
        <LaunchPane
          selectedAgent={selectedAgent}
          issueTitle={issueTitle}
          issueBody={issueDraftBody}
          launchText={launchText}
          busy={busy}
          onIssueTitleChange={onIssueTitleChange}
          onIssueBodyChange={onIssueDraftBodyChange}
          onLaunchTextChange={onLaunchTextChange}
          onPropose={onPropose}
          onAuditCleanup={onAuditCleanup}
          onPruneCleanup={onPruneCleanup}
          onCreateIssue={onCreateIssue}
          onBatchReview={onBatchReview}
          onBatchClaimNext={onBatchClaimNext}
          onPruneMerged={onPruneMerged}
        />
      ) : null}
      {pane === 'notifications' ? (
        <NotificationsPane
          notifications={notifications}
          loading={notificationsLoading}
          onRefresh={onRefreshNotifications}
        />
      ) : null}
    </main>
  );
}
