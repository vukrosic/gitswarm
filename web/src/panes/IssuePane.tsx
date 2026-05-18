import type { Issue } from '../types';
import { renderMarkdown } from '../markdown';

interface IssuePaneProps {
  issue: Issue;
  body: string;
  onBodyChange: (body: string) => void;
  onClaim: () => void;
  onReview: () => void;
  onSave: () => void;
  onDelete: () => void;
}

export function IssuePane({ issue, body, onBodyChange, onClaim, onReview, onSave, onDelete }: IssuePaneProps) {
  return (
    <section className="detail">
      <div className="detail-head">
        <div>
          <div className="eyebrow">Issue #{issue.number}</div>
          <h2>{issue.title}</h2>
          <div className="chips">
            {issue.labels.map((label) => <span key={label} className={`chip ${label}`}>{label}</span>)}
          </div>
        </div>
        <div className="detail-actions">
          <button onClick={onClaim}>Claim</button>
          <button onClick={onReview}>Review</button>
          <button onClick={onSave}>Save body</button>
          <button className="danger" onClick={onDelete}>Delete</button>
        </div>
      </div>
      <div className="rendered markdown">
        <div className="eyebrow">Rendered</div>
        <div dangerouslySetInnerHTML={{ __html: renderMarkdown(body) }} />
      </div>
    </section>
  );
}
