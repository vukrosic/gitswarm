import type { PtySession } from '../types';
import { useEffect, useMemo, useRef } from 'react';
import { ago } from '../lib/time';
import { renderTerminalText } from '../lib/terminal';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { PaneHeader, PaneShell } from './_shared';

interface TerminalPaneProps {
  pty: PtySession;
  input: string;
  log: string;
  offset: number;
  alive: boolean;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onCtrlC: () => void;
  onClose: () => void;
  onDelete: () => void;
}

export function TerminalPane({
  pty,
  input,
  log,
  offset,
  alive,
  onInputChange,
  onSend,
  onCtrlC,
  onClose,
  onDelete,
}: TerminalPaneProps) {
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const displayLog = useMemo(
    () => renderTerminalText(log, { rows: pty.rows || 30, cols: pty.cols || 120 }),
    [log, pty.rows, pty.cols],
  );

  useEffect(() => {
    inputRef.current?.focus();
  }, [pty.sid]);

  return (
    <PaneShell>
      <PaneHeader
        eyebrow={`PTY ${pty.sid}`}
        title={pty.label}
        meta={`${pty.cwd} · ${pty.alive ? 'alive' : 'dead'} · ${ago(pty.last_output)}`}
        actions={
          <>
            <Button variant="primary" size="sm" onClick={onSend}>Send</Button>
            <Button variant="outline" size="sm" onClick={onCtrlC}>Ctrl-C</Button>
            <Button variant="outline" size="sm" onClick={onClose}>Close</Button>
            <Button variant="danger" size="sm" onClick={onDelete}>Delete</Button>
          </>
        }
      />
      <Textarea
        ref={inputRef}
        autoFocus
        value={input}
        onChange={(event) => onInputChange(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            onSend();
          }
        }}
        placeholder="Type shell input and hit Send"
        className="min-h-[96px] resize-y font-mono"
      />
      <pre className="scrollbar-thin m-0 min-h-0 flex-1 overflow-auto whitespace-pre rounded-2xl border border-border bg-background/80 p-4 font-mono text-[12px] leading-snug text-foreground [tab-size:8] shadow-[inset_0_1px_0_hsl(0_0%_100%/0.03)]">
        {displayLog || 'Waiting for output...'}
      </pre>
      <div className="text-[11px] text-muted-foreground">
        offset {offset} · {alive ? 'streaming' : 'stopped'}
      </div>
    </PaneShell>
  );
}
