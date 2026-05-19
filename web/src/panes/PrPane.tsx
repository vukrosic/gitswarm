import type { GitHubComment, GitHubReview, GitHubReviewComment, PullRequest } from '../types';
import { renderMarkdown } from '../markdown';
import { Button } from '@/components/ui/button';
import { PaneHeader, PaneShell } from './_shared';
import { usePrCiStatus } from '../hooks/usePrCiStatus';

function CiDot({ status }: { status: string }) {
  const colors = {
    pass: 'bg-success',
    fail: 'bg-destructive',
    pending: 'bg-warning',
    unknown: 'bg-muted',
  };
  const cls = colors[status as keyof typeof colors] ?? colors.unknown;
  return <span className={`inline-block h-2 w-2 rounded-full ${cls} shrink-0`} />;
}

function CiStatusBadge({ name, status }: { name: string; status: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-full border border-border/70 bg-background/60 px-2 py-0.5 text-[10px] font-medium text-foreground">
      <CiDot status={status} />
      <span className="truncate max-w-[120px]">{name}</span>
    </span>
  );
}

interface PrPaneProps {
  pr: PullRequest;
  diff: string;
  onReview: () => void;
  onMerge: () => void;
  onFixCi: () => void;
}

function MarkdownBlock({ body }: { body: string }) {
  return (
    <div
      className="markdown break-words text-sm leading-relaxed text-foreground"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(body || '') }}
    />
  );
}

function CommentBlock({ comment }: { comment: GitHubComment }) {
  return (
    <article className="min-w-0 rounded-2xl border border-border/70 bg-background/60 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">{comment.author || 'unknown'}</span>
        <span>{comment.created_at ? new Date(comment.created_at).toLocaleString() : ''}</span>
      </div>
      <MarkdownBlock body={comment.body} />
    </article>
  );
}

function ReviewBlock({ review }: { review: GitHubReview }) {
  return (
    <article className="min-w-0 rounded-2xl border border-border/70 bg-background/60 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">{review.author || 'unknown'} · {review.state || 'review'}</span>
        <span>{review.submitted_at ? new Date(review.submitted_at).toLocaleString() : ''}</span>
      </div>
      {review.body ? <MarkdownBlock body={review.body} /> : (
        <div className="text-sm text-muted-foreground">No review body.</div>
      )}
    </article>
  );
}

function ReviewCommentBlock({ comment }: { comment: GitHubReviewComment }) {
  return (
    <article className="min-w-0 rounded-2xl border border-border/70 bg-background/60 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">
          {comment.author || 'unknown'} · {comment.path || 'review comment'}{comment.line ? `:${comment.line}` : ''}
        </span>
        <span>{comment.created_at ? new Date(comment.created_at).toLocaleString() : ''}</span>
      </div>
      {comment.diff_hunk ? (
        <pre className="mb-3 overflow-auto rounded-xl border border-border/70 bg-background/80 p-3 font-mono text-[11px] leading-relaxed text-muted-foreground">
          {comment.diff_hunk}
        </pre>
      ) : null}
      <MarkdownBlock body={comment.body} />
    </article>
  );
}

export function PrPane({ pr, diff, onReview, onMerge, onFixCi }: PrPaneProps) {
  const chips = [...(pr.labels || [])];
  const ciChecks = usePrCiStatus(pr.number);
  const ciChips = ciChecks.length > 0 ? ciChecks.map((c) => (
    <CiStatusBadge key={c.name} name={c.name} status={c.status} />
  )) : null;
  const comments = pr.comments || [];
  const reviews = pr.reviews || [];
  const reviewComments = pr.review_comments || [];
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
        ].filter(Boolean).join(' · ')}
        chips={chips}
        ciChips={ciChips}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={onReview}>Review</Button>
            <Button variant="primary" size="sm" onClick={onMerge}>Merge</Button>
            <Button variant="outline" size="sm" onClick={onFixCi}>Fix CI</Button>
          </>
        }
      />
      <div className="min-w-0 rounded-2xl border border-border/70 bg-background/60 p-5">
        <div className="mb-2 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Body</div>
        {pr.body ? <MarkdownBlock body={pr.body} /> : (
          <div className="text-sm text-muted-foreground">No PR body.</div>
        )}
      </div>
      <div className="min-w-0 space-y-2.5">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Comments</div>
        {comments.length ? comments.map((comment, index) => (
          <CommentBlock key={comment.id || index} comment={comment} />
        )) : (
          <div className="rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
            No issue comments yet.
          </div>
        )}
      </div>
      <div className="min-w-0 space-y-2.5">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Reviews</div>
        {reviews.length ? reviews.map((review, index) => (
          <ReviewBlock key={review.id || index} review={review} />
        )) : (
          <div className="rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
            No reviews yet.
          </div>
        )}
      </div>
      <div className="min-w-0 space-y-2.5">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Review comments</div>
        {reviewComments.length ? reviewComments.map((comment, index) => (
          <ReviewCommentBlock key={comment.id || index} comment={comment} />
        )) : (
          <div className="rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
            No inline review comments yet.
          </div>
        )}
      </div>
      <pre className="scrollbar-thin m-0 min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded-2xl border border-border bg-background/80 p-4 font-mono text-[12px] leading-relaxed text-foreground shadow-[inset_0_1px_0_hsl(0_0%_100%/0.03)]">
        {diff || 'Loading diff...'}
      </pre>
    </PaneShell>
  );
}
