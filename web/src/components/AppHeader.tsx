import type { Agent } from '../types';

interface AppHeaderProps {
  agents: Agent[];
  defaultAgent: string;
  selectedAgent: string;
  busy: string;
  onAgentChange: (agent: string) => void;
  onNewShell: () => void;
  onNewAgent: () => void;
  onRefresh: () => void;
}

export function AppHeader({
  agents,
  defaultAgent,
  selectedAgent,
  busy,
  onAgentChange,
  onNewShell,
  onNewAgent,
  onRefresh,
}: AppHeaderProps) {
  return (
    <header className="topbar">
      <div className="topbar-copy">
        <div className="eyebrow">gitswarm</div>
        <h1>Repository control room</h1>
        <p className="topbar-subtitle">Claims, reviews, worktrees, and live terminals in one calm surface.</p>
      </div>
      <div className="topbar-actions">
        <label className="select-wrap">
          <span>Agent</span>
          <select value={selectedAgent} onChange={(event) => onAgentChange(event.target.value)}>
            {agents.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.label}{agent.available ? '' : ' (missing)'}
              </option>
            ))}
            {!agents.length ? <option value={defaultAgent}>{defaultAgent}</option> : null}
          </select>
        </label>
        <button type="button" onClick={onNewShell} disabled={!!busy} title="Open an interactive shell in the right terminal dock">
          + new shell
        </button>
        <button type="button" onClick={onNewAgent} disabled={!!busy} title="Open the selected CLI agent in the right terminal dock">
          + new agent
        </button>
        <button onClick={onRefresh} disabled={!!busy}>Refresh</button>
      </div>
    </header>
  );
}
