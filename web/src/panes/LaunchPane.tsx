import type { Agent } from '../types';

interface LaunchPaneProps {
  agents: Agent[];
  selectedAgent: string;
  issueTitle: string;
  issueBody: string;
  launchText: string;
  onIssueTitleChange: (value: string) => void;
  onIssueBodyChange: (value: string) => void;
  onLaunchTextChange: (value: string) => void;
  onNewShell: () => void;
  onAgentShell: () => void;
  onPropose: () => void;
  onAuditCleanup: () => void;
  onPruneCleanup: () => void;
  onCreateIssue: () => void;
  onBatchReview: () => void;
  onBatchClaimNext: () => void;
  onPruneMerged: () => void;
}

export function LaunchPane({
  agents,
  selectedAgent,
  issueTitle,
  issueBody,
  launchText,
  onIssueTitleChange,
  onIssueBodyChange,
  onLaunchTextChange,
  onNewShell,
  onAgentShell,
  onPropose,
  onAuditCleanup,
  onPruneCleanup,
  onCreateIssue,
  onBatchReview,
  onBatchClaimNext,
  onPruneMerged,
}: LaunchPaneProps) {
  return (
    <section className="detail">
      <div className="detail-head">
        <div>
          <div className="eyebrow">Launchers</div>
          <h2>Agent / shell commands</h2>
        </div>
        <div className="detail-actions">
          <button onClick={onNewShell}>New shell</button>
          <button onClick={onAgentShell}>Agent shell</button>
          <button onClick={onPropose}>Propose</button>
          <button onClick={onAuditCleanup}>Audit cleanup</button>
          <button onClick={onPruneCleanup}>Prune cleanup</button>
        </div>
      </div>
      <div className="launch-grid">
        <section className="launch-card">
          <div className="eyebrow">Create issue</div>
          <label className="stack">
            <span>Title</span>
            <input value={issueTitle} onChange={(event) => onIssueTitleChange(event.target.value)} placeholder="Short issue title" />
          </label>
          <label className="stack">
            <span>Body</span>
            <textarea className="editor small" value={issueBody} onChange={(event) => onIssueBodyChange(event.target.value)} placeholder="Issue body" />
          </label>
          <div className="detail-actions">
            <button onClick={onCreateIssue}>Create issue</button>
          </div>
        </section>
        <section className="launch-card">
          <div className="eyebrow">Batch ops</div>
          <label className="stack">
            <span>Prompt / slug</span>
            <input value={launchText} onChange={(event) => onLaunchTextChange(event.target.value)} />
          </label>
          <div className="detail-actions">
            <button onClick={onBatchReview}>Batch review</button>
            <button onClick={onBatchClaimNext}>Batch claim-next</button>
            <button onClick={onPruneMerged}>Prune merged</button>
          </div>
          <div className="hint">Selected agent: {selectedAgent}</div>
        </section>
        <section className="launch-card">
          <div className="eyebrow">Agent status</div>
          <div className="chips">
            {agents.map((agent) => (
              <span key={agent.id} className={`chip ${agent.available ? 'ok' : 'missing'}`}>
                {agent.label}{agent.available ? '' : ' missing'}
              </span>
            ))}
          </div>
        </section>
      </div>
    </section>
  );
}
