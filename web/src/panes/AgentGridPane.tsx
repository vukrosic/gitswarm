import { useMemo, useState } from 'react';
import type { Agent, PtySession } from '../types';
import { ago } from '../lib/time';
import { renderTerminalText } from '../lib/terminal';
import { usePtyStream } from '@/hooks/usePtyStream';
import { cn } from '@/lib/utils';

export interface GridSession {
  sid: string;
  issue: number;
  label: string;
  alive: boolean;
  cwd: string;
  kind?: string;
  started?: number;
  last_output?: number;
  rows?: number;
  cols?: number;
}

interface AgentGridPaneProps {
  agents: Agent[];
  selectedAgent: string;
  onAgentChange: (agent: string) => void;
  onLaunch: (agent: string, issueNumbers: number[], cols: number, rows: number) => void;
  onFocusSession: (sid: string) => void;
  gridSessions: GridSession[];
  loading: boolean;
}

const GRID_CONFIGS = [
  { cols: 3, rows: 2, label: '3×2' },
  { cols: 2, rows: 3, label: '2×3' },
  { cols: 3, rows: 3, label: '3×3' },
];

function CellTerminal({ sid }: { sid: string }) {
  const { text, offset, alive } = usePtyStream(sid);
  const displayLog = useMemo(
    () => renderTerminalText(text, { rows: 20, cols: 80 }),
    [text],
  );
  return (
    <pre
      className={cn(
        'm-0 flex-1 overflow-auto whitespace-pre font-mono text-[11px] leading-snug text-foreground [tab-size:8]',
        !alive && 'opacity-60',
      )}
    >
      {displayLog || 'Waiting for output...'}
      <span className="block pt-1 text-[10px] text-muted-foreground/60">
        {alive ? 'streaming' : 'stopped'} · offset {offset}
      </span>
    </pre>
  );
}

export function AgentGridPane({
  agents,
  selectedAgent,
  onAgentChange,
  onLaunch,
  onFocusSession,
  gridSessions,
  loading,
}: AgentGridPaneProps) {
  const [gridConfig, setGridConfig] = useState(GRID_CONFIGS[0]);
  const [launching, setLaunching] = useState(false);

  const cellLabels = useMemo(() => {
    const result: string[] = [];
    for (let r = 0; r < gridConfig.rows; r += 1) {
      for (let c = 0; c < gridConfig.cols; c += 1) {
        result.push(String.fromCharCode(65 + r) + (c + 1));
      }
    }
    return result;
  }, [gridConfig]);

  const activeCells = gridConfig.rows * gridConfig.cols;

  async function handleLaunch() {
    if (!selectedAgent || activeCells === 0) return;
    setLaunching(true);
    try {
      // Build list of issue numbers from the first `activeCells` grid sessions
      // If not enough sessions, prompt user
      const issueNumbers = gridSessions.slice(0, activeCells).map((s) => s.issue);
      if (issueNumbers.length < activeCells) {
        alert(`Need ${activeCells} issues configured. Only ${issueNumbers.length} grid sessions available.`);
        return;
      }
      await onLaunch(selectedAgent, issueNumbers, gridConfig.cols, gridConfig.rows);
    } finally {
      setLaunching(false);
    }
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-hidden">
      {/* Launch controls */}
      <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-border bg-card/60 p-4">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Agent</span>
          <select
            value={selectedAgent}
            onChange={(e) => onAgentChange(e.target.value)}
            className="rounded-xl border border-border bg-background px-2 py-1 text-xs text-foreground focus:outline-none focus:ring-2 focus:ring-ring/40"
          >
            {agents.map((a) => (
              <option key={a.id} value={a.id}>
                {a.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Grid</span>
          <div className="flex gap-1">
            {GRID_CONFIGS.map((cfg) => (
              <button
                key={cfg.label}
                type="button"
                onClick={() => setGridConfig(cfg)}
                className={cn(
                  'rounded-lg border px-2.5 py-1 text-[11px] font-medium transition-all',
                  gridConfig.label === cfg.label
                    ? 'border-primary/60 bg-primary/20 text-foreground'
                    : 'border-border bg-card/40 text-muted-foreground hover:border-primary/40 hover:text-foreground',
                )}
              >
                {cfg.label}
              </button>
            ))}
          </div>
        </div>

        <button
          type="button"
          onClick={handleLaunch}
          disabled={launching || loading || agents.length === 0}
          className="rounded-xl border border-primary/60 bg-gradient-to-b from-primary/20 to-primary/5 px-4 py-1.5 text-xs font-medium text-foreground transition-all hover:border-primary/80 disabled:opacity-50"
        >
          {launching ? 'Launching...' : 'Launch Grid'}
        </button>

        <div className="ml-auto text-[11px] text-muted-foreground">
          {gridSessions.length} / {activeCells} cells active
        </div>
      </div>

      {/* Grid */}
      {gridSessions.length === 0 ? (
        <div className="flex flex-1 items-center justify-center rounded-2xl border border-dashed border-primary/30 bg-card/30">
          <div className="text-center">
            <p className="text-sm font-medium text-muted-foreground">No grid running</p>
            <p className="mt-1 text-xs text-muted-foreground/70">Launch a grid to see agents working in parallel</p>
          </div>
        </div>
      ) : (
        <div
          className="grid min-h-0 flex-1 gap-2 overflow-hidden"
          style={{
            gridTemplateColumns: `repeat(${gridConfig.cols}, 1fr)`,
          }}
        >
          {Array.from({ length: activeCells }).map((_, idx) => {
            const session = gridSessions[idx];
            const cellLabel = cellLabels[idx];
            if (!session) {
              return (
                <div
                  key={`empty-${idx}`}
                  className="flex min-h-0 overflow-hidden rounded-xl border border-dashed border-border/40 bg-card/20"
                >
                  <div className="flex w-full items-center justify-center text-[11px] text-muted-foreground/50">
                    {cellLabel} — empty
                  </div>
                </div>
              );
            }
            return (
              <div
                key={session.sid}
                className="flex min-h-0 flex-col overflow-hidden rounded-xl border border-border bg-card/80"
              >
                {/* Cell header */}
                <div className="flex items-center justify-between gap-2 border-b border-border/60 bg-background/60 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'h-2 w-2 rounded-full',
                        session.alive ? 'bg-success' : 'bg-muted-foreground/40',
                      )}
                    />
                    <span className="text-[11px] font-semibold text-foreground">{cellLabel}</span>
                    <span className="text-[11px] text-muted-foreground">#{session.issue}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => onFocusSession(session.sid)}
                    className="rounded-lg border border-border bg-card/40 px-2 py-0.5 text-[10px] text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
                  >
                    Focus
                  </button>
                </div>

                {/* PTY output */}
                <div className="flex min-h-0 flex-1 flex-col overflow-hidden p-2">
                  <CellTerminal sid={session.sid} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}