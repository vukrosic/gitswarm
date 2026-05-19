import type { Worktree } from '../types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { PaneHeader, PaneShell } from './_shared';

interface WorktreePaneProps {
  worktree: Worktree;
  busy: string;
  onShell: () => void;
  onRemove: () => void;
}

function worktreeTone(worktree: Worktree) {
  if (worktree.running) return 'warning';
  if (worktree.dirty) return 'destructive';
  if (worktree.safe_remove) return 'success';
  if (worktree.merged) return 'success';
  return 'default';
}

export function WorktreePane({ worktree, busy, onShell, onRemove }: WorktreePaneProps) {
  const canRemove = !!worktree.safe_remove && !worktree.running && !worktree.dirty;
  const shellLoading = busy === `shell ${worktree.name}`;
  const removeLoading = busy === `remove ${worktree.name}`;

  return (
    <PaneShell>
      <PaneHeader
        eyebrow="Worktree"
        title={worktree.name}
        meta={worktree.path || worktree.branch}
        chips={[
          worktree.status,
          worktree.running ? 'running' : '',
          worktree.dirty ? 'dirty' : '',
          worktree.safe_remove ? 'safe remove' : '',
        ].filter(Boolean) as string[]}
        actions={
          <>
            <Button variant="primary" size="sm" onClick={onShell} loading={shellLoading} disabled={!!busy}>
              Shell
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={onRemove}
              loading={removeLoading}
              disabled={!!busy || !canRemove}
              title={
                worktree.running
                  ? 'Wait for the active session to stop before removing this worktree'
                  : !worktree.safe_remove
                    ? 'Only merged, clean worktrees can be removed safely'
                    : undefined
              }
            >
              Remove
            </Button>
          </>
        }
      />

      <div className="grid gap-3 md:grid-cols-2">
        <InfoCard label="Branch" value={worktree.branch} />
        <InfoCard label="Status" value={worktree.status} tone={worktreeTone(worktree)} />
        <InfoCard label="Head" value={worktree.head || 'unknown'} />
        <InfoCard label="Commits" value={worktree.commits || 'none ahead of origin/main'} />
        <InfoCard label="Ahead" value={String(worktree.ahead)} />
        <InfoCard label="Behind" value={String(worktree.behind)} />
      </div>

      <div className="rounded-2xl border border-border/70 bg-card/45 p-4 text-[12px] leading-relaxed text-muted-foreground">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={worktree.running ? 'warning' : 'default'}>{worktree.running ? 'running' : 'idle'}</Badge>
          <Badge variant={worktree.dirty ? 'destructive' : worktree.safe_remove ? 'success' : 'default'}>
            {worktree.dirty ? 'dirty' : worktree.safe_remove ? 'safe to remove' : 'keep it'}
          </Badge>
          {typeof worktree.issue === 'number' ? <Badge variant="default">issue #{worktree.issue}</Badge> : null}
        </div>
        <div className="mt-3 grid gap-1.5">
          <Line label="Path" value={worktree.path || '(unknown)'} />
          <Line label="Head" value={worktree.head || '(unknown)'} />
          <Line label="Merged" value={worktree.merged ? 'yes' : 'no'} />
          <Line label="Running" value={worktree.running ? 'yes' : 'no'} />
          <Line label="Safe remove" value={worktree.safe_remove ? 'yes' : 'no'} />
        </div>
      </div>

      <details className="rounded-2xl border border-border/70 bg-background/70 p-4">
        <summary className="cursor-pointer text-sm font-medium text-foreground">
          Raw response
        </summary>
        <pre className="scrollbar-thin mt-3 overflow-auto whitespace-pre-wrap rounded-xl bg-card/40 p-4 font-mono text-[12px] leading-relaxed text-foreground">
          {JSON.stringify(worktree, null, 2)}
        </pre>
      </details>
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
      <div className="mt-1.5 break-all text-sm leading-snug text-foreground">
        {tone !== 'default' ? <Badge variant={tone} className="mb-2">{tone}</Badge> : null}
        <div>{value}</div>
      </div>
    </div>
  );
}

function Line({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex gap-3 text-[12px]">
      <span className="w-28 shrink-0 font-medium text-muted-foreground">{label}</span>
      <span className="min-w-0 break-all font-mono text-foreground">{value}</span>
    </div>
  );
}
