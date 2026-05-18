import type { PullRequest } from '../types';
import { Button } from '@/components/ui/button';
import { PaneHeader, PaneShell } from './_shared';

interface PrPaneProps {
  pr: PullRequest;
  diff: string;
  onReview: () => void;
  onMerge: () => void;
  onFixCi: () => void;
}

export function PrPane({ pr, diff, onReview, onMerge, onFixCi }: PrPaneProps) {
  const chips = [...pr.labels, ...(pr.ci ? [pr.ci] : [])];
  return (
    <PaneShell>
      <PaneHeader
        eyebrow={`PR #${pr.number}`}
        title={pr.title}
        meta={`branch ${pr.head} · base ${pr.base} · ${pr.author}`}
        chips={chips}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={onReview}>Review</Button>
            <Button variant="primary" size="sm" onClick={onMerge}>Merge</Button>
            <Button variant="outline" size="sm" onClick={onFixCi}>Fix CI</Button>
          </>
        }
      />
      <pre className="scrollbar-thin m-0 min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded-2xl border border-border bg-background/80 p-4 font-mono text-[12px] leading-relaxed text-foreground shadow-[inset_0_1px_0_hsl(0_0%_100%/0.03)]">
        {diff || 'Loading diff...'}
      </pre>
    </PaneShell>
  );
}
