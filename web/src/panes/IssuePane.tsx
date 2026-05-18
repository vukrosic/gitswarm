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
    <PaneShell>
      <PaneHeader
        eyebrow={`Issue #${issue.number}`}
        title={issue.title}
        chips={issue.labels}
        actions={
          <>
            <Button variant="primary" size="sm" onClick={onClaim}>Claim</Button>
            <Button variant="outline" size="sm" onClick={onReview}>Review</Button>
            <Button variant="outline" size="sm" onClick={onSave}>Save body</Button>
            <Button variant="danger" size="sm" onClick={onDelete}>Delete</Button>
          </>
        }
      />
      <div className="rounded-2xl border border-border/70 bg-background/60 p-5">
        <div className="mb-2 text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">Rendered</div>
        <div
          className="markdown text-sm leading-relaxed text-foreground"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }}
        />
      </div>
    </PaneShell>
  );
}
