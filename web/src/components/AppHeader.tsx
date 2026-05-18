import { Plus, RefreshCw, Terminal as TerminalIcon } from 'lucide-react';
import type { Agent } from '../types';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

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
  const agentOptions = agents.length ? agents : [{ id: defaultAgent, label: defaultAgent, available: true, bin: '' } as Agent];

  return (
    <header className="sticky top-0 z-40 flex flex-wrap items-center justify-between gap-4 border-b border-border/60 bg-background/70 px-6 py-4 backdrop-blur-xl shadow-[0_10px_30px_hsl(0_0%_0%/0.22)]">
      <div className="flex min-w-0 flex-col gap-0.5">
        <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">
          gitswarm
        </span>
        <h1 className="text-lg font-semibold tracking-tight text-foreground sm:text-xl">
          Repository control room
        </h1>
        <p className="max-w-[58ch] text-xs leading-relaxed text-muted-foreground">
          Claims, reviews, worktrees, and live terminals in one calm surface.
          {busy ? <span className="ml-2 text-warning">· {busy}…</span> : null}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Agent
          </span>
          <Select value={selectedAgent} onValueChange={onAgentChange}>
            <SelectTrigger className="h-9 w-[180px]">
              <SelectValue placeholder="Select agent" />
            </SelectTrigger>
            <SelectContent>
              {agentOptions.map((agent) => (
                <SelectItem key={agent.id} value={agent.id}>
                  <span className="flex items-center gap-2">
                    {agent.label}
                    {!agent.available ? (
                      <span className="text-[10px] uppercase tracking-wide text-destructive">missing</span>
                    ) : null}
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="mt-[18px] flex flex-wrap items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={!!busy}
            onClick={onNewShell}
            title="Open an interactive shell in the right terminal dock"
          >
            <Plus className="h-3.5 w-3.5" />
            new shell
          </Button>
          <Button
            variant="primary"
            size="sm"
            disabled={!!busy}
            onClick={onNewAgent}
            title="Open the selected CLI agent in the right terminal dock"
          >
            <TerminalIcon className="h-3.5 w-3.5" />
            new agent
          </Button>
          <Button variant="ghost" size="sm" onClick={onRefresh} disabled={!!busy} title="Refresh dashboard">
            <RefreshCw className="h-3.5 w-3.5" />
            Refresh
          </Button>
        </div>
      </div>
    </header>
  );
}
