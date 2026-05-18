import type { Worktree } from '../types';

interface WorktreePaneProps {
  worktree: Worktree;
  onShell: () => void;
  onRemove: () => void;
}

export function WorktreePane({ worktree, onShell, onRemove }: WorktreePaneProps) {
  return (
    <section className="detail">
      <div className="detail-head">
        <div>
          <div className="eyebrow">Worktree</div>
          <h2>{worktree.name}</h2>
          <div className="meta-line">{worktree.branch} · {worktree.status}</div>
        </div>
        <div className="detail-actions">
          <button onClick={onShell}>Shell</button>
          <button className="danger" onClick={onRemove}>Remove</button>
        </div>
      </div>
      <pre className="body">{JSON.stringify(worktree, null, 2)}</pre>
    </section>
  );
}
