import { ChevronLeft, ChevronRight, Plus, RefreshCw, Terminal as TerminalIcon } from 'lucide-react';
import type { Agent, Project } from '../types';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

interface AppHeaderProps {
  projects: Project[];
  activeProject: Project | null;
  agents: Agent[];
  defaultAgent: string;
  selectedAgent: string;
  busy: string;
  dockCollapsed: boolean;
  onProjectChange: (projectId: string) => void;
  onAgentChange: (agent: string) => void;
  onNewShell: () => void;
  onNewAgent: () => void;
  onRefresh: () => void;
  onToggleDock: () => void;
}

export function AppHeader({
  projects,
  activeProject,
  agents,
  defaultAgent,
  selectedAgent,
  busy,
  dockCollapsed,
  onProjectChange,
  onAgentChange,
  onNewShell,
  onNewAgent,
  onRefresh,
  onToggleDock,
}: AppHeaderProps) {
  const projectOptions = projects.length ? projects : activeProject ? [activeProject] : [];
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
        {activeProject ? (
          <p className="max-w-[58ch] text-[11px] leading-relaxed text-muted-foreground/80">
            Project: {activeProject.label} · {activeProject.repo_root}
          </p>
        ) : null}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">
            Project
          </span>
          <Select value={activeProject?.id || ''} onValueChange={onProjectChange}>
            <SelectTrigger className="h-9 w-[260px]">
              <SelectValue placeholder="Select project" />
            </SelectTrigger>
            <SelectContent>
              {projectOptions.map((project) => (
                <SelectItem key={project.id} value={project.id}>
                  <span className="flex flex-col items-start gap-0.5">
                    <span className="flex items-center gap-2">
                      {project.label}
                      {project.active ? <span className="text-[10px] uppercase tracking-wide text-success">active</span> : null}
                    </span>
                    <span className="text-[10px] text-muted-foreground">{project.repo_root}</span>
                  </span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

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
          <Button
            variant="outline"
            size="sm"
            onClick={onToggleDock}
            className="h-9 w-9 px-0"
            title={dockCollapsed ? 'Open terminal dock' : 'Collapse terminal dock'}
            aria-label={dockCollapsed ? 'Open terminal dock' : 'Collapse terminal dock'}
          >
            {dockCollapsed ? (
              <ChevronLeft className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </div>
    </header>
  );
}
