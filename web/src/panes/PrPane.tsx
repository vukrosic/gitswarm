import type { PullRequest } from '../types';

interface PrPaneProps {
  pr: PullRequest;
  diff: string;
  onReview: () => void;
  onMerge: () => void;
  onFixCi: () => void;
}

export function PrPane({ pr, diff, onReview, onMerge, onFixCi }: PrPaneProps) {
  return (
    <section className="detail">
      <div className="detail-head">
        <div>
          <div className="eyebrow">PR #{pr.number}</div>
          <h2>{pr.title}</h2>
          <div className="chips">
            {pr.labels.map((label) => <span key={label} className={`chip ${label}`}>{label}</span>)}
            {pr.ci ? <span className={`chip ${pr.ci}`}>{pr.ci}</span> : null}
          </div>
        </div>
        <div className="detail-actions">
          <button onClick={onReview}>Review</button>
          <button onClick={onMerge}>Merge</button>
          <button onClick={onFixCi}>Fix CI</button>
        </div>
      </div>
      <div className="meta-line">branch {pr.head} · base {pr.base} · {pr.author}</div>
      <pre className="diff">{diff || 'Loading diff...'}</pre>
    </section>
  );
}
