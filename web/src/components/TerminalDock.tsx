import type { ClipboardEvent, KeyboardEvent, UIEvent } from 'react';
import type { PtySession } from '../types';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ptyResize } from '../api';
import { ago } from '../lib/time';
import { sessionLabel } from '../lib/labels';
import { renderTerminalText } from '../lib/terminal';

interface TerminalDockProps {
  pty: PtySession | null;
  sessions: PtySession[];
  log: string;
  offset: number;
  alive: boolean;
  collapsed: boolean;
  onClose: () => void;
  onDelete: () => void;
  onToggle: () => void;
  onNewAgent: () => void;
  onFocusSession: (pty: PtySession) => void;
  onType: (value: string) => void;
}

interface TerminalSize {
  rows: number;
  cols: number;
}

let measureCanvas: HTMLCanvasElement | null = null;

function cssPixels(value: string) {
  const parsed = Number.parseFloat(value);
  return Number.isFinite(parsed) ? parsed : 0;
}

function measureTerminalSize(element: HTMLElement): TerminalSize {
  const style = window.getComputedStyle(element);
  if (!measureCanvas) measureCanvas = document.createElement('canvas');
  const context = measureCanvas.getContext('2d');
  const fontSize = cssPixels(style.fontSize) || 12;
  const lineHeight = cssPixels(style.lineHeight) || fontSize * 1.35;
  let charWidth = fontSize * 0.62;
  if (context) {
    context.font = style.font || `${style.fontWeight} ${style.fontSize} ${style.fontFamily}`;
    const measured = context.measureText('M'.repeat(40)).width / 40;
    if (Number.isFinite(measured) && measured > 0) charWidth = measured;
  }

  const width = element.clientWidth - cssPixels(style.paddingLeft) - cssPixels(style.paddingRight);
  const height = element.clientHeight - cssPixels(style.paddingTop) - cssPixels(style.paddingBottom);
  return {
    rows: Math.max(8, Math.min(80, Math.floor(height / lineHeight))),
    cols: Math.max(24, Math.min(220, Math.floor(width / charWidth))),
  };
}

export function TerminalDock({
  pty,
  sessions,
  log,
  offset,
  alive,
  collapsed,
  onClose,
  onDelete,
  onToggle,
  onNewAgent,
  onFocusSession,
  onType,
}: TerminalDockProps) {
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const outputRef = useRef<HTMLPreElement | null>(null);
  const stickToBottomRef = useRef(true);
  const lastResizeRef = useRef('');
  const [terminalSize, setTerminalSize] = useState<TerminalSize>({
    rows: pty?.rows || 30,
    cols: pty?.cols || 120,
  });
  const displayLog = useMemo(
    () => renderTerminalText(log, terminalSize),
    [log, terminalSize.rows, terminalSize.cols],
  );

  useEffect(() => {
    if (pty && !collapsed) {
      terminalRef.current?.focus();
    }
  }, [pty?.sid, collapsed]);

  useEffect(() => {
    stickToBottomRef.current = true;
    if (!collapsed) {
      outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
    }
  }, [pty?.sid, collapsed]);

  useEffect(() => {
    const next = { rows: pty?.rows || 30, cols: pty?.cols || 120 };
    lastResizeRef.current = `${next.rows}x${next.cols}`;
    setTerminalSize(next);
  }, [pty?.sid]);

  useEffect(() => {
    if (!pty || collapsed || typeof ResizeObserver === 'undefined') return undefined;
    const output = outputRef.current;
    if (!output) return undefined;

    let frame = 0;
    const updateSize = () => {
      const next = measureTerminalSize(output);
      const key = `${next.rows}x${next.cols}`;
      if (lastResizeRef.current === key) return;
      lastResizeRef.current = key;
      setTerminalSize(next);
      void ptyResize(pty.sid, next.rows, next.cols).catch(() => {});
    };
    const scheduleSize = () => {
      if (frame) window.cancelAnimationFrame(frame);
      frame = window.requestAnimationFrame(updateSize);
    };

    const observer = new ResizeObserver(scheduleSize);
    observer.observe(output);
    scheduleSize();

    return () => {
      if (frame) window.cancelAnimationFrame(frame);
      observer.disconnect();
    };
  }, [pty?.sid, collapsed]);

  useEffect(() => {
    const output = outputRef.current;
    if (!output || !stickToBottomRef.current) return;
    output.scrollTop = output.scrollHeight;
  }, [displayLog]);

  function handleKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    if (!pty) return;

    if (event.ctrlKey && event.key.toLowerCase() === 'c') {
      event.preventDefault();
      onType('\u0003');
      return;
    }

    if (event.key === 'Enter') {
      event.preventDefault();
      onType('\n');
      return;
    }

    if (event.key === 'Backspace') {
      event.preventDefault();
      onType('\u007f');
      return;
    }

    if (event.key === 'Tab') {
      event.preventDefault();
      onType('\t');
      return;
    }

    if (event.key.length === 1 && !event.metaKey && !event.altKey && !event.ctrlKey) {
      event.preventDefault();
      onType(event.key);
    }
  }

  function handlePaste(event: ClipboardEvent<HTMLDivElement>) {
    if (!pty) return;
    const text = event.clipboardData.getData('text');
    if (!text) return;
    event.preventDefault();
    onType(text);
  }

  function handleOutputScroll(event: UIEvent<HTMLPreElement>) {
    const output = event.currentTarget;
    const distanceFromBottom = output.scrollHeight - output.scrollTop - output.clientHeight;
    stickToBottomRef.current = distanceFromBottom < 24;
  }

  return (
    <section className={`terminal-dock ${collapsed ? 'collapsed' : ''}`} aria-label="Manual terminal dock">
      <div className="dock-head">
        <div>
          <div className="eyebrow">Dock</div>
          <h3>{pty ? sessionLabel(pty) : 'manual shells & agents'}</h3>
          <div className="meta-line">
            {pty ? `${pty.cwd || 'repo'} · ${pty.alive ? 'alive' : 'dead'} · ${ago(pty.last_output)}` : 'Use + new shell or + new agent for manual typing.'}
          </div>
        </div>
        <div className="dock-actions">
          <button type="button" onClick={onNewAgent}>+ agent</button>
          <button type="button" onClick={onClose} disabled={!pty}>Close</button>
          <button type="button" onClick={onToggle}>{collapsed ? 'Open' : 'Collapse'}</button>
        </div>
      </div>

      {!collapsed ? (
        <>
          <div className="terminal-tabs" aria-label="Manual terminal sessions">
            {sessions.map((session) => (
              <button
                key={session.sid}
                type="button"
                className={pty?.sid === session.sid ? 'on' : ''}
                onClick={() => onFocusSession(session)}
                title={session.cwd}
              >
                {sessionLabel(session)}
              </button>
            ))}
            {!sessions.length ? <span>No manual sessions yet</span> : null}
          </div>

          <div className="dock-body">
            {pty ? (
              <div
                ref={terminalRef}
                className="dock-terminal-surface"
                tabIndex={0}
                role="textbox"
                aria-multiline="true"
                aria-label="Manual terminal input"
                onKeyDown={handleKeyDown}
                onPaste={handlePaste}
              >
                <pre
                  ref={outputRef}
                  className="terminal-view dock-terminal-view"
                  onScroll={handleOutputScroll}
                >
                  {displayLog || 'Waiting for output...'}
                </pre>
                <div className="dock-terminal-hint">Click here and type. Enter sends, Backspace deletes, Ctrl-C interrupts.</div>
                <div className="meta-line">offset {offset} · {alive ? 'streaming' : 'stopped'}</div>
              </div>
            ) : (
              <div className="dock-empty">
                <strong>Manual terminal dock</strong>
                <span>Header + new shell opens a repo shell here.</span>
                <span>Dock + agent opens the selected agent here.</span>
                <span>Claim, review, merge, fix CI, and propose stay in the middle pane.</span>
              </div>
            )}
          </div>
        </>
      ) : null}
    </section>
  );
}
