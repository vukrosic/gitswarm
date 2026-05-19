import { useState } from 'react';
import type { Issue, Milestone } from '../types';
import { fmtTime } from '../lib/time';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PaneHeader, PaneShell } from './_shared';
import { closeMilestone } from '@/api/client';

interface MilestonePaneProps {
  milestone: Milestone;
  issues: Issue[];
  onFocusIssue: (issue: Issue) => void;
  onOpenGitHub: () => void;
}

function toneForState(state: string) {
  return state === 'open' ? 'success' : 'default';
}

export function MilestonePane({ milestone, issues, onFocusIssue, onOpenGitHub }: MilestonePaneProps) {
  const [closing, setClosing] = useState(false);
  const relatedIssues = issues.filter((issue) => issue.milestone?.number === milestone.number);
  const dueAt = milestone.due_on ? new Date(milestone.due_on).toLocaleDateString() : 'no due date';
  const createdAt = milestone.created_at ? fmtTime(Date.parse(milestone.created_at) / 1000) : '';
  const updatedAt = milestone.updated_at ? fmtTime(Date.parse(milestone.updated_at) / 1000) : '';

  async function handleClose() {
    if (closing) return;
    setClosing(true);
    try {
      await closeMilestone(milestone.number);
    } finally {
      setClosing(false);
    }
  }

  return (
    <PaneShell>
      <PaneHeader
        eyebrow={`Milestone #${milestone.number}`}
        title={milestone.title}
        meta={milestone.description || dueAt}
        chips={[
          milestone.state,
          `${milestone.open_issues} open`,
          `${milestone.closed_issues} closed`,
          milestone.due_on ? `due ${dueAt}` : '',
        ].filter(Boolean) as string[]}
        actions={
          <>
            {milestone.state === 'open' && (
              <Button
                variant={closing ? 'muted' : 'destructive'}
                size="sm"
                onClick={handleClose}
                disabled={closing}
              >
                {closing ? 'Closing…' : 'Close milestone'}
              </Button>
            )}
            <Button variant="primary" size="sm" onClick={onOpenGitHub} disabled={!milestone.url}>
              Open on GitHub
            </Button>
          </>
        }
      />

      <div className="grid gap-3 md:grid-cols-2">
        <InfoCard label="State" value={milestone.state} tone={toneForState(milestone.state)} />
        <InfoCard label="Open issues" value={String(milestone.open_issues)} />
        <InfoCard label="Closed issues" value={String(milestone.closed_issues)} />
        <InfoCard label="Due" value={milestone.due_on ? dueAt : 'none'} />
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/45 p-4">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Description</div>
        <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-foreground">
          {milestone.description || 'No milestone description yet.'}
        </p>
        <div className="mt-3 text-[11px] text-muted-foreground">
          {createdAt ? `Created ${createdAt}` : ''}
          {updatedAt ? `${createdAt ? ' · ' : ''}Updated ${updatedAt}` : ''}
        </div>
      </div>

      <div className="rounded-2xl border border-border/70 bg-background/70 p-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Linked issues</div>
            <div className="mt-1 text-sm text-foreground">{relatedIssues.length} issue{relatedIssues.length === 1 ? '' : 's'}</div>
          </div>
          <Badge variant={milestone.state === 'open' ? 'success' : 'default'}>{milestone.state}</Badge>
        </div>

        <div className="mt-3 grid gap-1.5">
          {relatedIssues.length ? (
            relatedIssues.map((issue) => (
              <button
                key={issue.number}
                type="button"
                onClick={() => onFocusIssue(issue)}
                className="flex items-start justify-between gap-3 rounded-xl border border-border/70 bg-card/50 px-3 py-2 text-left transition-all hover:-translate-y-px hover:border-primary/40 hover:bg-card"
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-medium text-foreground">#{issue.number} {issue.title}</div>
                  <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
                    {issue.state} · {issue.milestone?.title || 'no milestone'}
                  </div>
                </div>
                <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground">
                  view
                </span>
              </button>
            ))
          ) : (
            <div className="rounded-xl border border-dashed border-border/60 bg-card/30 p-4 text-center text-xs text-muted-foreground">
              No open issues currently point at this milestone.
            </div>
          )}
        </div>
      </div>
    </PaneShell>
  );
}

function InfoCard({
  label,
  value,
  tone = 'default',
}: {
  label: string;
  value: string;
  tone?: 'default' | 'success' | 'warning' | 'destructive';
}) {
  return (
    <div className="rounded-2xl border border-border/70 bg-card/45 p-4">
      <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <div className="mt-1.5 text-sm leading-snug text-foreground">
        {tone !== 'default' ? <Badge variant={tone} className="mb-2">{tone}</Badge> : null}
        <div>{value}</div>
      </div>
    </div>
  );
}
