import type { GitHubComment, Issue } from '../types';
import { renderMarkdown } from '../markdown';
import { Button } from '@/components/ui/button';
import { PaneHeader, PaneShell } from './_shared';

interface IssuePaneProps {
  issue: Issue;
  body: string;
  busy: string;
  onBodyChange: (body: string) => void;
  onOpenIssueCreator: () => void;
  onClaim: () => void;
  onReview: () => void;
  onSave: () => void;
  onDelete: () => void;
}

function CommentBlock({ comment }: { comment: GitHubComment }) {
  return (
    <article className="min-w-0 rounded-2xl border border-border/70 bg-background/60 p-4">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2 text-[11px] text-muted-foreground">
        <span className="font-medium text-foreground">{comment.author || 'unknown'}</span>
        <span>{comment.created_at ? new Date(comment.created_at).toLocaleString() : ''}</span>
      </div>
      <div
        className="markdown break-words text-sm leading-relaxed text-foreground"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(comment.body || '') }}
      />
    </article>
  );
}

export function IssuePane({
  issue,
  body,
  busy,
  onBodyChange: _onBodyChange,
  onOpenIssueCreator,
  onClaim,
  onReview,
  onSave,
  onDelete,
}: IssuePaneProps) {
  const comments = issue.comments || [];
  const claimLoading = busy === `claim #${issue.number}`;
  const reviewLoading = busy === `review #${issue.number}`;
  const saveLoading = busy === `update #${issue.number}`;
  const deleteLoading = busy === `delete #${issue.number}`;
  return (
    <PaneShell className="min-w-0">
      <PaneHeader
        eyebrow={`Issue #${issue.number}`}
        title={issue.title}
        meta={[
          issue.author ? `opened by ${issue.author}` : '',
          issue.state || '',
          `${comments.length || issue.comment_count || 0} comments`,
        ].filter(Boolean).join(' · ')}
        chips={[
          ...(issue.labels || []),
          issue.milestone?.title ? `milestone: ${issue.milestone.title}` : '',
        ].filter(Boolean) as string[]}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={onOpenIssueCreator} disabled={!!busy}>New issue</Button>
            <Button
              variant="primary"
              size="sm"
              onClick={onClaim}
              loading={claimLoading}
              disabled={!!busy}
              title="Spawn an agent (Claude/Codex) in a fresh worktree branch for this issue and drop you into its terminal"
            >
              Claim
            </Button>
            <Button variant="outline" size="sm" onClick={onReview} loading={reviewLoading} disabled={!!busy}>
              Review
            </Button>
            {issue.url ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(issue.url, '_blank', 'noopener,noreferrer')}
                disabled={!!busy}
              >
                Open on GitHub
              </Button>
            ) : null}
            <Button variant="outline" size="sm" onClick={onSave} loading={saveLoading} disabled={!!busy}>
              Save body
            </Button>
            <Button variant="danger" size="sm" onClick={onDelete} loading={deleteLoading} disabled={!!busy}>
              Delete
            </Button>
          </>
        }
      />
      <div className="min-w-0 rounded-2xl border border-border/70 bg-background/60 p-5">
        <div className="mb-2 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Body</div>
        <div
          className="markdown break-words text-sm leading-relaxed text-foreground"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }}
        />
      </div>
      <div className="min-w-0 space-y-2.5">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          Comments
        </div>
        {comments.length ? comments.map((comment, index) => (
          <CommentBlock key={comment.id || index} comment={comment} />
        )) : (
          <div className="rounded-2xl border border-dashed border-border/70 bg-background/40 p-4 text-sm text-muted-foreground">
            No comments yet.
          </div>
        )}
      </div>
    </PaneShell>
  );
}
