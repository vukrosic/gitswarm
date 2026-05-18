import type { PtySession } from '../types';
import { useMemo } from 'react';
import { ago } from '../lib/time';
import { renderTerminalText } from '../lib/terminal';

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
  const displayLog = useMemo(
    () => renderTerminalText(log, { rows: pty.rows || 30, cols: pty.cols || 120 }),
    [log, pty.rows, pty.cols],
  );

  return (
    <section className="detail terminal">
      <div className="detail-head">
        <div>
          <div className="eyebrow">PTY {pty.sid}</div>
          <h2>{pty.label}</h2>
          <div className="meta-line">{pty.cwd} · {pty.alive ? 'alive' : 'dead'} · {ago(pty.last_output)}</div>
        </div>
        <div className="detail-actions">
          <button onClick={onSend}>Send</button>
          <button onClick={onCtrlC}>Ctrl-C</button>
          <button onClick={onClose}>Close</button>
          <button className="danger" onClick={onDelete}>Delete</button>
        </div>
      </div>
      <textarea className="pty-input" value={input} onChange={(e) => onInputChange(e.target.value)} placeholder="Type shell input and hit Send" />
      <pre className="terminal-view">{displayLog || 'Waiting for output...'}</pre>
      <div className="meta-line">offset {offset} · {alive ? 'streaming' : 'stopped'}</div>
    </section>
  );
}
