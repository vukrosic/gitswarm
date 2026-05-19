import type { Agent, Project } from '../types';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { PaneHeader, PaneShell } from './_shared';

interface LaunchPaneProps {
  projects: Project[];
  activeProject: Project | null;
  agents: Agent[];
  selectedAgent: string;
  issueTitle: string;
  issueBody: string;
  launchText: string;
  projectPath: string;
  onIssueTitleChange: (value: string) => void;
  onIssueBodyChange: (value: string) => void;
  onLaunchTextChange: (value: string) => void;
  onProjectPathChange: (value: string) => void;
  onNewShell: () => void;
  onAgentShell: () => void;
  onPropose: () => void;
  onAddProject: () => void;
  onAuditCleanup: () => void;
  onPruneCleanup: () => void;
  onCreateIssue: () => void;
  onBatchReview: () => void;
  onBatchClaimNext: () => void;
  onPruneMerged: () => void;
}

function LaunchCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-2xl border border-border/70 bg-background/40 p-4">
      <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{title}</div>
      {children}
    </section>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5 text-[11px] text-muted-foreground">
      <span>{label}</span>
      {children}
    </label>
  );
}

export function LaunchPane({
  projects,
  activeProject,
  agents,
  selectedAgent,
  issueTitle,
  issueBody,
  launchText,
  projectPath,
  onIssueTitleChange,
  onIssueBodyChange,
  onLaunchTextChange,
  onProjectPathChange,
  onNewShell,
  onAgentShell,
  onPropose,
  onAddProject,
  onAuditCleanup,
  onPruneCleanup,
  onCreateIssue,
  onBatchReview,
  onBatchClaimNext,
  onPruneMerged,
}: LaunchPaneProps) {
  return (
    <PaneShell>
      <PaneHeader
        eyebrow="Launchers"
        title="Agent / shell commands"
        actions={
          <>
            <Button variant="outline" size="sm" onClick={onNewShell}>New shell</Button>
            <Button variant="primary" size="sm" onClick={onAgentShell}>Agent shell</Button>
            <Button variant="outline" size="sm" onClick={onPropose}>Propose</Button>
            <Button variant="outline" size="sm" onClick={onAuditCleanup}>Audit cleanup</Button>
            <Button variant="outline" size="sm" onClick={onPruneCleanup}>Prune cleanup</Button>
          </>
        }
      />
      <div className="grid gap-3 lg:grid-cols-3">
        <LaunchCard title="Create issue">
          <Field label="Title">
            <Input
              value={issueTitle}
              onChange={(event) => onIssueTitleChange(event.target.value)}
              placeholder="Short issue title"
            />
          </Field>
          <Field label="Body">
            <Textarea
              value={issueBody}
              onChange={(event) => onIssueBodyChange(event.target.value)}
              placeholder="Issue body"
              className="min-h-[140px] resize-y"
            />
          </Field>
          <div className="flex justify-start">
            <Button variant="primary" size="sm" onClick={onCreateIssue}>Create issue</Button>
          </div>
        </LaunchCard>

        <LaunchCard title="Batch ops">
          <Field label="Prompt / slug">
            <Input value={launchText} onChange={(event) => onLaunchTextChange(event.target.value)} />
          </Field>
          <div className="flex flex-wrap gap-1.5">
            <Button variant="outline" size="sm" onClick={onBatchReview}>Batch review</Button>
            <Button variant="outline" size="sm" onClick={onBatchClaimNext}>Batch claim-next</Button>
            <Button variant="outline" size="sm" onClick={onPruneMerged}>Prune merged</Button>
          </div>
          <div className="text-[11px] text-muted-foreground">Selected agent: {selectedAgent}</div>
        </LaunchCard>

        <LaunchCard title="Agent status">
          <div className="flex flex-wrap gap-1.5">
            {agents.map((agent) => (
              <Badge key={agent.id} variant={agent.available ? 'success' : 'destructive'}>
                {agent.label}
                {agent.available ? '' : ' · missing'}
              </Badge>
            ))}
          </div>
        </LaunchCard>

        <LaunchCard title="Projects">
          <Field label="Repo path">
            <Input
              value={projectPath}
              onChange={(event) => onProjectPathChange(event.target.value)}
              placeholder="/path/to/another/repo"
            />
          </Field>
          <div className="flex justify-start gap-2">
            <Button variant="primary" size="sm" onClick={onAddProject}>
              Add project
            </Button>
          </div>
          <div className="space-y-1 text-[11px] text-muted-foreground">
            <div>Active project: {activeProject ? activeProject.label : 'none'}</div>
            <div>{projects.length} registered project{projects.length === 1 ? '' : 's'}</div>
          </div>
        </LaunchCard>
      </div>
    </PaneShell>
  );
}
