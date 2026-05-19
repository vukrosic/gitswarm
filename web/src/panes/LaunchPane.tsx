import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { PaneHeader, PaneShell } from './_shared';

interface LaunchPaneProps {
  selectedAgent: string;
  issueTitle: string;
  issueBody: string;
  launchText: string;
  busy: string;
  onIssueTitleChange: (value: string) => void;
  onIssueBodyChange: (value: string) => void;
  onLaunchTextChange: (value: string) => void;
  onPropose: () => void;
  onAuditCleanup: () => void;
  onPruneCleanup: () => void;
  onCreateIssue: () => void;
  onBatchReview: () => void;
  onBatchClaimNext: () => void;
  onPruneMerged: () => void;
}

function LaunchCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-2xl border border-border/70 bg-background/40 p-4">
      <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{title}</div>
      {children}
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-[11px] text-muted-foreground">
      <span>{label}</span>
      {children}
    </label>
  );
}

export function LaunchPane({
  selectedAgent,
  issueTitle,
  issueBody,
  launchText,
  busy,
  onIssueTitleChange,
  onIssueBodyChange,
  onLaunchTextChange,
  onPropose,
  onAuditCleanup,
  onPruneCleanup,
  onCreateIssue,
  onBatchReview,
  onBatchClaimNext,
  onPruneMerged,
}: LaunchPaneProps) {
  const createLoading = busy === 'create issue';
  const proposeLoading = busy === 'propose';
  const auditLoading = busy === 'cleanup audit';
  const pruneLoading = busy === 'cleanup prune';
  const batchReviewLoading = busy === 'batch review' || busy.startsWith('review #');
  const batchClaimLoading = busy === 'batch claim-next' || busy.startsWith('claim #');
  const pruneMergedLoading = busy === 'prune merged worktrees';
  return (
    <PaneShell>
      <PaneHeader
        eyebrow="Launchers"
        title="Create issue"
      />
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1.35fr)_minmax(0,0.85fr)]">
        <LaunchCard title="Write it down">
          <Field label="Title">
            <Input
              value={issueTitle}
              onChange={(event) => onIssueTitleChange(event.target.value)}
              placeholder="Short issue title"
            />
          </Field>
          <Field label="Body">
            <Textarea
              value={issueBody}
              onChange={(event) => onIssueBodyChange(event.target.value)}
              placeholder="Issue body"
              className="min-h-[190px] resize-y"
            />
          </Field>
          <div className="flex justify-start">
            <Button variant="primary" size="sm" onClick={onCreateIssue} loading={createLoading} disabled={!!busy}>
              Create issue
            </Button>
          </div>
        </LaunchCard>

        <LaunchCard title="Advanced">
          <div className="space-y-3">
            <Field label="Prompt / slug">
              <Input value={launchText} onChange={(event) => onLaunchTextChange(event.target.value)} />
            </Field>
            <div className="flex flex-wrap gap-1.5">
              <Button variant="outline" size="sm" onClick={onPropose} loading={proposeLoading} disabled={!!busy}>
                Propose
              </Button>
              <Button variant="outline" size="sm" onClick={onAuditCleanup} loading={auditLoading} disabled={!!busy}>
                Audit cleanup
              </Button>
              <Button variant="outline" size="sm" onClick={onPruneCleanup} loading={pruneLoading} disabled={!!busy}>
                Prune cleanup
              </Button>
              <Button variant="outline" size="sm" onClick={onBatchReview} loading={batchReviewLoading} disabled={!!busy}>
                Batch review
              </Button>
              <Button variant="outline" size="sm" onClick={onBatchClaimNext} loading={batchClaimLoading} disabled={!!busy}>
                Batch claim-next
              </Button>
              <Button variant="outline" size="sm" onClick={onPruneMerged} loading={pruneMergedLoading} disabled={!!busy}>
                Prune merged
              </Button>
            </div>
            <div className="text-[11px] text-muted-foreground">Selected agent: {selectedAgent}</div>
          </div>
        </LaunchCard>
      </div>
    </PaneShell>
  );
}
