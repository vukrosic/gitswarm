import { useMemo, type ReactNode } from 'react';
import type { PullRequest } from '../types';
import { renderMarkdown } from '../markdown';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { PaneHeader, PaneShell } from './_shared';
import { usePrCiStatus } from '../hooks/usePrCiStatus';
import { ago } from '../lib/time';

interface PrPaneProps {
  pr: PullRequest;
  diff: string;
  onOpenGitHub: () => void;
  busy: string;
  onReview: () => void;
  onMerge: () => void;
  onFixCi: () => void;
}

type TimelineKind = 'comment' | 'review' | 'inline';

interface TimelineItem {
  kind: TimelineKind;
  id: string;
  author: string;
  body: string;
  ts: number;
  meta: string;
  diffHunk?: string;
}

interface CheckSummary {
  total: number;
  pass: number;
  pending: number;
  fail: number;
  unknown: number;
  label: string;
  tone: 'default' | 'success' | 'warning' | 'destructive' | 'info';
  hint: string;
}

function MarkdownBlock({ body }: { body: string }) {
  return (
    <div
      className="markdown break-words text-sm leading-relaxed text-foreground"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(body || '') }}
    />
  );
}

function tsFrom(...values: Array<string | undefined | null>) {
  for (const value of values) {
    if (!value) continue;
    const ts = Date.parse(value);
    if (Number.isFinite(ts)) return ts;
  }
  return 0;
}

function statusTone(status: string): 'default' | 'success' | 'warning' | 'destructive' | 'info' {
  const normalized = (status || '').toLowerCase();
  if (normalized === 'pass' || normalized === 'approved' || normalized === 'mergeable' || normalized === 'ready') {
    return 'success';
  }
  if (normalized === 'pending' || normalized === 'watching' || normalized === 'draft' || normalized === 'waiting') {
    return 'warning';
  }
  if (normalized === 'fail' || normalized === 'blocked' || normalized === 'conflicting' || normalized === 'changes requested') {
    return 'destructive';
  }
  if (normalized === 'info' || normalized === 'review') {
    return 'info';
  }
  return 'default';
}

function summarizeChecks(checks: Array<{ status: string }>, pr: PullRequest): CheckSummary {
  const counts = { pass: 0, pending: 0, fail: 0, unknown: 0 };
  for (const check of checks) {
    const status = (check.status || '').toLowerCase();
    if (status === 'pass') counts.pass += 1;
    else if (status === 'pending') counts.pending += 1;
    else if (status === 'fail') counts.fail += 1;
    else counts.unknown += 1;
  }
  const total = checks.length;
  if (!total) {
    const overall = (pr.ci || '').toLowerCase();
    if (overall === 'ok') counts.pass = 1;
    else if (overall === 'pending') counts.pending = 1;
    else if (overall === 'fail') counts.fail = 1;
    else counts.unknown = 1;
  }
  const effectiveTotal = Math.max(total, 1);
  let label = 'unknown';
  let tone: CheckSummary['tone'] = 'default';
  let hint = 'no check data yet';
  if (counts.fail > 0) {
    label = 'blocked';
    tone = 'destructive';
    hint = 'failing checks need attention';
  } else if (counts.pending > 0) {
    label = 'watching';
    tone = 'warning';
    hint = 'checks are still running';
  } else if (counts.pass > 0) {
    label = 'passing';
    tone = 'success';
    hint = 'checks are green';
  }
  return {
    total: effectiveTotal,
    pass: counts.pass,
    pending: counts.pending,
    fail: counts.fail,
    unknown: counts.unknown,
    label,
    tone,
    hint,
  };
}

function buildTimeline(pr: PullRequest): TimelineItem[] {
  const items: TimelineItem[] = [];
  (pr.comments || []).forEach((comment, index) => {
    items.push({
      kind: 'comment',
      id: `comment-${comment.id || index}`,
      author: comment.author || 'unknown',
      body: comment.body || '',
      ts: tsFrom(comment.created_at, comment.updated_at),
      meta: 'issue comment',
    });
  });
  (pr.reviews || []).forEach((review, index) => {
    items.push({
      kind: 'review',
      id: `review-${review.id || index}`,
      author: review.author || 'unknown',
      body: review.body || '',
      ts: tsFrom(review.submitted_at),
      meta: review.state || 'review',
    });
  });
  (pr.review_comments || []).forEach((comment, index) => {
    const location = [comment.path || 'inline', comment.line ? `:${comment.line}` : ''].join('');
    items.push({
      kind: 'inline',
      id: `inline-${comment.id || index}`,
      author: comment.author || 'unknown',
      body: comment.body || '',
      ts: tsFrom(comment.created_at, comment.updated_at),
      meta: location,
      diffHunk: comment.diff_hunk || '',
    });
  });
  return items.sort((a, b) => b.ts - a.ts);
}

function deriveChecks(pr: PullRequest, ciChecks: Array<{ name: string; status: string }>) {
  if (ciChecks.length) return ciChecks;
  const fallback: Array<{ name: string; status: string }> = [];
  if (pr.failing_checks?.length) {
    fallback.push(...pr.failing_checks.map((name) => ({ name, status: 'fail' })));
  }
  if (pr.pending_checks?.length) {
    fallback.push(...pr.pending_checks.map((name) => ({ name, status: 'pending' })));
  }
  if (!fallback.length && pr.ci) {
    fallback.push({ name: 'overall', status: pr.ci });
  }
  return fallback;
}

function SectionCard({
  title,
  eyebrow,
  children,
  className = '',
}: {
  title: string;
  eyebrow?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`min-w-0 rounded-2xl border border-border/70 bg-background/60 p-4 ${className}`}>
      <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{eyebrow || title}</div>
      {eyebrow ? <h3 className="mt-1 text-sm font-semibold text-foreground">{title}</h3> : null}
      <div className={eyebrow ? 'mt-3' : 'mt-2'}>{children}</div>
    </section>
  );
}

function StatCard({
  label,
  value,
  tone,
  hint,
}: {
  label: string;
  value: string;
  tone: CheckSummary['tone'];
  hint: string;
}) {
  return (
    <section className="rounded-2xl border border-border/70 bg-background/60 p-4">
      <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{label}</div>
      <div className="mt-2 flex items-center justify-between gap-3">
        <div className="text-sm font-semibold capitalize tracking-tight text-foreground">{value}</div>
        <Badge variant={tone}>{value}</Badge>
      </div>
      <div className="mt-2 text-[11px] text-muted-foreground">{hint}</div>
    </section>
  );
}

function TimelineRow({ item }: { item: TimelineItem }) {
  return (
    <article className="min-w-0 rounded-2xl border border-border/70 bg-background/60 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">
          {item.author} · <span className="uppercase tracking-wide">{item.kind}</span>
        </span>
        <span>{item.ts ? new Date(item.ts).toLocaleString() : ''}</span>
      </div>
      <div className="mb-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
        {item.meta || item.kind}
      </div>
      {item.diffHunk ? (
        <pre className="mb-3 overflow-auto rounded-xl border border-border/70 bg-background/80 p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">
          {item.diffHunk}
        </pre>
      ) : null}
      <MarkdownBlock body={item.body} />
    </article>
  );
}

function CheckRow({ name, status }: { name: string; status: string }) {
  const tone = statusTone(status);
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-card/40 px-3 py-2">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-foreground">{name}</div>
      </div>
      <Badge variant={tone}>{status || 'unknown'}</Badge>
    </div>
  );
}

export function PrPane({ pr, diff, onOpenGitHub, busy, onReview, onMerge, onFixCi }: PrPaneProps) {
  const ciChecks = usePrCiStatus(pr.number);
  const displayChecks = useMemo(() => deriveChecks(pr, ciChecks), [pr, ciChecks]);
  const ciSummary = useMemo(() => summarizeChecks(displayChecks, pr), [displayChecks, pr]);
  const timeline = useMemo(() => buildTimeline(pr), [pr]);
  const comments = pr.comments || [];
  const reviews = pr.reviews || [];
  const reviewComments = pr.review_comments || [];
  const reviewDecision = (pr.reviewDecision || '').toUpperCase();
  const mergeable = (pr.mergeable || '').toUpperCase();
  const reviewLoading = busy === `review PR #${pr.number}`;
  const mergeLoading = busy === `merge PR #${pr.number}`;
  const fixCiLoading = busy === `fix-ci PR #${pr.number}`;

  const readiness = useMemo(() => {
    if (pr.isDraft) {
      return { value: 'draft', tone: 'warning' as const, hint: 'still in draft mode' };
    }
    if (mergeable === 'CONFLICTING') {
      return { value: 'blocked', tone: 'destructive' as const, hint: 'merge conflicts need a fix' };
    }
    if (ciSummary.fail > 0) {
      return { value: 'blocked', tone: 'destructive' as const, hint: 'CI is failing' };
    }
    if (ciSummary.pending > 0) {
      return { value: 'watching', tone: 'warning' as const, hint: 'CI is still running' };
    }
    if (reviewDecision === 'CHANGES_REQUESTED') {
      return { value: 'blocked', tone: 'destructive' as const, hint: 'changes were requested' };
    }
    if (reviewDecision === 'APPROVED' && mergeable === 'MERGEABLE') {
      return { value: 'ready', tone: 'success' as const, hint: 'looks mergeable and approved' };
    }
    if (reviewDecision === 'APPROVED') {
      return { value: 'approved', tone: 'success' as const, hint: 'approved, mergeability still settling' };
    }
    return { value: 'review', tone: 'info' as const, hint: 'needs a human review pass' };
  }, [ciSummary.fail, ciSummary.pending, mergeable, pr.isDraft, reviewDecision]);

  const latestActivity = timeline[0];
  const discussionTotal = comments.length + reviews.length + reviewComments.length;

  return (
    <PaneShell>
      <PaneHeader
        eyebrow={`PR #${pr.number}`}
        title={pr.title}
        meta={[
          pr.head ? `branch ${pr.head}` : '',
          pr.base ? `base ${pr.base}` : '',
          pr.author || '',
          `${comments.length} comments`,
          `${reviews.length} reviews`,
          `${reviewComments.length} review comments`,
          latestActivity?.ts ? `updated ${ago(Math.floor(latestActivity.ts / 1000))}` : '',
        ].filter(Boolean).join(' · ')}
        chips={[
          ...(pr.labels || []),
          pr.isDraft ? 'draft' : 'open',
          mergeable ? `mergeable: ${mergeable.toLowerCase()}` : '',
          reviewDecision ? `review: ${reviewDecision.toLowerCase().replace('_', ' ')}` : '',
        ].filter(Boolean) as string[]}
        ciChips={
          <>
            <Badge variant={readiness.tone}>{readiness.value}</Badge>
            <Badge variant={ciSummary.tone}>
              {ciSummary.pass} pass · {ciSummary.pending} pending · {ciSummary.fail} fail
            </Badge>
          </>
        }
        actions={
          <>
            <Button variant="outline" size="sm" onClick={onOpenGitHub}>Open on GitHub</Button>
            <Button variant="outline" size="sm" onClick={onReview}>Review</Button>
            <Button variant="primary" size="sm" onClick={onMerge}>Merge</Button>
            <Button variant="outline" size="sm" onClick={onFixCi}>Fix CI</Button>
          </>
        }
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <StatCard label="Readiness" value={readiness.value} tone={readiness.tone} hint={readiness.hint} />
        <StatCard
          label="Review"
          value={reviewDecision ? reviewDecision.toLowerCase().replace('_', ' ') : 'none'}
          tone={statusTone(reviewDecision || 'review')}
          hint={reviewDecision ? 'latest review outcome' : 'waiting for a review'}
        />
        <StatCard
          label="Merge"
          value={mergeable ? mergeable.toLowerCase() : 'unknown'}
          tone={statusTone(mergeable || 'unknown')}
          hint={pr.isDraft ? 'drafts stay blocked' : 'mergeability from GitHub'}
        />
        <StatCard
          label="CI"
          value={`${ciSummary.pass} pass / ${ciSummary.pending} pending / ${ciSummary.fail} fail`}
          tone={ciSummary.tone}
          hint={ciSummary.hint}
        />
        <StatCard
          label="Discussion"
          value={`${discussionTotal} items`}
          tone="info"
          hint={latestActivity?.ts ? `latest ${ago(Math.floor(latestActivity.ts / 1000))}` : 'no discussion yet'}
        />
      </div>

      <div className="grid min-h-0 gap-3 xl:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)]">
        <div className="flex min-w-0 flex-col gap-3">
          <SectionCard title="Body" eyebrow="Overview">
            {pr.body ? <MarkdownBlock body={pr.body} /> : (
              <div className="text-sm text-muted-foreground">No PR body.</div>
            )}
          </SectionCard>

          <SectionCard title="Discussion timeline" eyebrow="Conversation">
            <div className="space-y-2.5">
              {timeline.length ? timeline.map((item) => (
                <TimelineRow key={item.id} item={item} />
              )) : (
                <div className="rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
                  No discussion yet.
                </div>
              )}
            </div>
          </SectionCard>
        </div>

        <div className="flex min-w-0 flex-col gap-3">
          <SectionCard title="Checks" eyebrow="Signals">
            <div className="space-y-1.5">
              {displayChecks.length ? displayChecks.map((check) => (
                <CheckRow key={check.name} name={check.name} status={check.status} />
              )) : (
                <div className="rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
                  No check data yet.
                </div>
              )}
            </div>
          </SectionCard>

          <SectionCard title="Diff" eyebrow="Patch" className="flex min-h-0 flex-1 flex-col">
            <pre className="scrollbar-thin m-0 min-h-[28rem] flex-1 overflow-auto whitespace-pre-wrap rounded-2xl border border-border bg-background/80 p-4 font-mono text-[12px] leading-relaxed text-foreground shadow-[inset_0_1px_0_hsl(0_0%_100%/0.03)]">
              {diff || 'Loading diff...'}
            </pre>
          </SectionCard>
        </div>
      </div>
    </PaneShell>
  );
}
