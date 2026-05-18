import type { Worktree } from '../types';
import { Button } from '@/components/ui/button';
import { PaneHeader, PaneShell } from './_shared';

interface WorktreePaneProps {
  worktree: Worktree;
  onShell: () => void;
  onRemove: () => void;
}

export function WorktreePane({ worktree, onShell, onRemove }: WorktreePaneProps) {
  return (
    <PaneShell>
      <PaneHeader
        eyebrow="Worktree"
        title={worktree.name}
        meta={`${worktree.branch} · ${worktree.status}`}
        actions={
          <>
            <Button variant="primary" size="sm" onClick={onShell}>Shell</Button>
            <Button variant="danger" size="sm" onClick={onRemove}>Remove</Button>
          </>
        }
      />
      <pre className="scrollbar-thin m-0 min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded-2xl border border-border bg-background/80 p-4 font-mono text-[12px] leading-relaxed text-foreground shadow-[inset_0_1px_0_hsl(0_0%_100%/0.03)]">
        {JSON.stringify(worktree, null, 2)}
      </pre>
    </PaneShell>
  );
}
