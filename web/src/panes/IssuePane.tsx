import type { Issue } from '../types';
import { renderMarkdown } from '../markdown';
import { Button } from '@/components/ui/button';
import { PaneHeader, PaneShell } from './_shared';

interface IssuePaneProps {
  issue: Issue;
  body: string;
  onBodyChange: (body: string) => void;
  onClaim: () => void;
  onReview: () => void;
  onSave: () => void;
  onDelete: () => void;
}

export function IssuePane({ issue, body, onBodyChange: _onBodyChange, onClaim, onReview, onSave, onDelete }: IssuePaneProps) {
  return (
    <PaneShell className="min-w-0">
      <PaneHeader
        eyebrow={`Issue #${issue.number}`}
        title={issue.title}
        chips={[
          ...issue.labels,
          issue.milestone?.title ? `milestone: ${issue.milestone.title}` : '',
        ].filter(Boolean) as string[]}
        actions={
          <>
            <Button
              variant="primary"
              size="sm"
              onClick={onClaim}
              title="Spawn an agent (Claude/Codex) in a fresh worktree branch for this issue and drop you into its terminal"
            >
              Claim
            </Button>
            <Button variant="outline" size="sm" onClick={onReview}>Review</Button>
            {issue.url ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => window.open(issue.url, '_blank', 'noopener,noreferrer')}
              >
                Open on GitHub
              </Button>
            ) : null}
            <Button variant="outline" size="sm" onClick={onSave}>Save body</Button>
            <Button variant="danger" size="sm" onClick={onDelete}>Delete</Button>
          </>
        }
      />
      <div className="min-w-0 rounded-2xl border border-border/70 bg-background/60 p-5">
        <div className="mb-2 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Rendered</div>
        <div
          className="markdown break-words text-sm leading-relaxed text-foreground"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }}
        />
      </div>
    </PaneShell>
  );
}
