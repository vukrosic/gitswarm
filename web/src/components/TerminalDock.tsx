import type { ClipboardEvent, KeyboardEvent, UIEvent } from 'react';
import type { PtySession } from '../types';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Plus, Terminal as TerminalIcon, X, Pencil } from 'lucide-react';
import { ptyResize, ptyRename } from '../api';
import { ago } from '../lib/time';
import { sessionLabel } from '../lib/labels';
import { renderTerminalText } from '../lib/terminal';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

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
  onDelete: _onDelete,
  onToggle,
  onNewAgent,
  onFocusSession,
  onType,
}: TerminalDockProps) {
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const outputRef = useRef<HTMLPreElement | null>(null);
  const stickToBottomRef = useRef(true);
  const lastResizeRef = useRef('');
  const [terminalSize, setTerminalSize] = useState<TerminalSize>({
    rows: pty?.rows || 30,
    cols: pty?.cols || 120,
  });
  const [renamingSid, setRenamingSid] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');
  const focusTerminal = () => {
    terminalRef.current?.focus();
    inputRef.current?.focus();
  };
  const captureKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (!pty) return;
    if (event.ctrlKey && event.key.toLowerCase() === 'c') {
      event.preventDefault();
      onType('\u0003');
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      onType(event.shiftKey ? '\n' : '\r');
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
  };
  const displayLog = useMemo(
    () => renderTerminalText(log, terminalSize),
    [log, terminalSize.rows, terminalSize.cols],
  );

  useEffect(() => {
    if (pty && !collapsed) {
      terminalRef.current?.focus();
      inputRef.current?.focus();
    }
  }, [pty?.sid, collapsed]);

  useEffect(() => {
    stickToBottomRef.current = true;
    if (!collapsed) outputRef.current?.scrollTo({ top: outputRef.current.scrollHeight });
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

  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
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

  function startRename(session: PtySession) {
    setRenamingSid(session.sid);
    setRenameValue(session.label || session.sid);
  }

  function handleRenameKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      const sid = renamingSid;
      if (sid) {
        void ptyRename(sid, renameValue).then(() => {
          setRenamingSid(null);
        });
      }
    } else if (event.key === 'Escape') {
      setRenamingSid(null);
    }
  }

  function handleRenameBlur() {
    const sid = renamingSid;
    if (sid) {
      void ptyRename(sid, renameValue).then(() => {
        setRenamingSid(null);
      });
    }
  }

  if (collapsed) {
    return (
      <section
        aria-label="Manual terminal dock"
        className={cn(
          'flex min-h-0 flex-col overflow-hidden rounded-[var(--radius)] border border-border bg-gradient-to-b from-card/90 to-background/95 shadow-[0_24px_70px_hsl(0_0%_0%/0.42)] backdrop-blur-xl',
          'w-full',
        )}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border/60 bg-background/40 p-3.5">
          <div className="min-w-0 flex-1">
            <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">Dock</div>
            <h3 className="mt-0.5 truncate text-sm font-semibold tracking-tight text-foreground">
              {pty ? sessionLabel(pty) : 'manual shells & agents'}
            </h3>
            <div className="mt-1 truncate text-[11px] text-muted-foreground">
              Collapsed. Open to show sessions and terminal output.
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onToggle}>
            <ChevronLeft className="h-3 w-3" />
            Open
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-1.5 p-3">
          <Button variant="outline" size="sm" onClick={onNewAgent}>
            <Plus className="h-3 w-3" />
            agent
          </Button>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={!pty}>
            <X className="h-3 w-3" />
            Close
          </Button>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-label="Manual terminal dock"
      className="flex min-h-0 flex-col overflow-hidden rounded-[var(--radius)] border border-border bg-gradient-to-b from-card/90 to-background/95 shadow-[0_24px_70px_hsl(0_0%_0%/0.42)] backdrop-blur-xl"
    >
      <div className="flex items-start justify-between gap-3 border-b border-border/60 bg-background/40 p-3.5">
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-medium uppercase tracking-[0.16em] text-muted-foreground">Dock</div>
          <h3 className="mt-0.5 truncate text-sm font-semibold tracking-tight text-foreground">
            {pty ? sessionLabel(pty) : 'manual shells & agents'}
          </h3>
          <div className="mt-1 truncate text-[11px] text-muted-foreground">
            {pty
              ? `${pty.cwd || 'repo'} · ${pty.alive ? 'alive' : 'dead'} · ${ago(pty.last_output)}`
              : 'Use + new shell or + new agent for manual typing.'}
          </div>
        </div>
        <div className="flex shrink-0 flex-wrap items-center justify-end gap-1.5">
          <Button variant="outline" size="sm" onClick={onNewAgent}>
            <Plus className="h-3 w-3" />
            agent
          </Button>
          <Button variant="ghost" size="sm" onClick={onClose} disabled={!pty}>
            <X className="h-3 w-3" />
            Close
          </Button>
          <Button variant="ghost" size="sm" onClick={onToggle}>
            <ChevronRight className="h-3 w-3" />
            Collapse
          </Button>
        </div>
      </div>

      {!collapsed ? (
        <>
          <div
            className="scrollbar-thin flex gap-1.5 overflow-x-auto border-b border-border/60 bg-background/30 px-3 py-2"
            aria-label="Manual terminal sessions"
          >
            {sessions.map((session) => {
              const on = pty?.sid === session.sid;
              const isRenaming = renamingSid === session.sid;
              return (
                <button
                  key={session.sid}
                  type="button"
                  onClick={() => onFocusSession(session)}
                  title={session.cwd}
                  className={cn(
                    'inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-2.5 py-1 text-[11px] transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
                    on
                      ? 'border-success/60 bg-gradient-to-b from-success/20 to-success/5 text-foreground'
                      : 'border-border bg-card/40 text-muted-foreground hover:border-primary/40 hover:text-foreground',
                  )}
                >
                  <TerminalIcon className="h-3 w-3" />
                  {isRenaming ? (
                    <input
                      autoFocus
                      value={renameValue}
                      onChange={(e) => setRenameValue(e.target.value)}
                      onKeyDown={handleRenameKeyDown}
                      onBlur={handleRenameBlur}
                      onClick={(e) => e.stopPropagation()}
                      className="w-20 bg-transparent text-[11px] outline-none"
                    />
                  ) : (
                    <span className="max-w-[120px] truncate">{sessionLabel(session)}</span>
                  )}
                  {!isRenaming && (
                    <Pencil
                      className="h-3 w-3 cursor-pointer opacity-50 hover:opacity-100"
                      onClick={(e) => {
                        e.stopPropagation();
                        startRename(session);
                      }}
                    />
                  )}
                </button>
              );
            })}
            {!sessions.length ? (
              <span className="self-center text-[11px] text-muted-foreground">No manual sessions yet</span>
            ) : null}
          </div>

          <div className="flex min-h-0 flex-1 flex-col gap-2.5 bg-background/40 p-3">
            {pty ? (
              <div
                ref={terminalRef}
                className="flex min-h-0 flex-1 cursor-text flex-col gap-2 overflow-hidden rounded-2xl border border-border bg-background/80 p-3 outline-none transition-colors focus-visible:border-primary/70 focus-visible:shadow-[0_0_0_2px_hsl(var(--primary)/0.16)]"
              >
                <pre
                  ref={outputRef}
                  onScroll={handleOutputScroll}
                  className="scrollbar-thin m-0 min-h-0 flex-1 overflow-auto whitespace-pre font-mono text-[12px] leading-snug text-foreground [tab-size:8] [overscroll-behavior:contain]"
                >
                  {displayLog || 'Waiting for output...'}
                </pre>
                <Textarea
                  ref={inputRef}
                  readOnly
                  value=""
                  aria-label="Manual terminal input"
                  onFocus={focusTerminal}
                  onMouseDown={focusTerminal}
                  onKeyDown={captureKeyDown}
                  onPaste={handlePaste}
                  onClick={focusTerminal}
                  className="min-h-[56px] resize-none border-border/70 bg-background/75 font-mono text-[12px] text-foreground placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-primary/30"
                  placeholder="Click here and type. Enter sends, Shift+Enter for newline, Ctrl-C interrupts."
                />
                <div className="text-[11px] text-muted-foreground">
                  offset {offset} · {alive ? 'streaming' : 'stopped'}
                </div>
              </div>
            ) : (
              <div className="flex min-h-[240px] flex-1 flex-col items-start justify-center gap-1.5 rounded-2xl border border-dashed border-primary/30 bg-background/60 p-5">
                <strong className="text-sm text-foreground">Manual terminal dock</strong>
                <span className="text-xs text-muted-foreground">Header + new shell opens a repo shell here.</span>
                <span className="text-xs text-muted-foreground">Dock + agent opens the selected agent here.</span>
                <span className="text-xs text-muted-foreground">Claim, review, merge, fix CI, and propose stay in the middle pane.</span>
              </div>
            )}
          </div>
        </>
      ) : null}
    </section>
  );
}
