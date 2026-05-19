import type { PtySession } from '../types';
import type { ClipboardEvent, KeyboardEvent, UIEvent } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { ago } from '../lib/time';
import { renderTerminalText } from '../lib/terminal';
import { ptyResize } from '../api';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { PaneHeader, PaneShell } from './_shared';

interface TerminalPaneProps {
  pty: PtySession;
  log: string;
  offset: number;
  alive: boolean;
  busy: string;
  onType: (value: string) => void;
  onClose: () => void;
  onDelete: () => void;
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

export function TerminalPane({
  pty,
  log,
  offset,
  alive,
  busy,
  onType,
  onClose,
  onDelete,
}: TerminalPaneProps) {
  const terminalRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const outputRef = useRef<HTMLPreElement | null>(null);
  const stickToBottomRef = useRef(true);
  const lastResizeRef = useRef('');
  const [terminalSize, setTerminalSize] = useState<TerminalSize>({
    rows: pty.rows || 30,
    cols: pty.cols || 120,
  });
  const closeLoading = busy === `close pty ${pty.sid}`;
  const deleteLoading = busy === `delete pty ${pty.sid}`;
  const displayLog = useMemo(
    () => renderTerminalText(log, terminalSize),
    [log, terminalSize.rows, terminalSize.cols],
  );

  const focusTerminal = () => {
    terminalRef.current?.focus();
    inputRef.current?.focus();
  };

  const captureKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.ctrlKey && event.key.toLowerCase() === 'c') {
      event.preventDefault();
      onType('');
      return;
    }
    if (event.key === 'Enter') {
      event.preventDefault();
      onType(event.shiftKey ? '\n' : '\r');
      return;
    }
    if (event.key === 'Backspace') {
      event.preventDefault();
      onType('');
      return;
    }
    if (event.key === 'Tab') {
      event.preventDefault();
      onType('\t');
      return;
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault();
      onType('[A');
      return;
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      onType('[B');
      return;
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      onType('[C');
      return;
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      onType('[D');
      return;
    }
    if (event.key === 'Escape') {
      event.preventDefault();
      onType('');
      return;
    }
    if (event.key.length === 1 && !event.metaKey && !event.altKey && !event.ctrlKey) {
      event.preventDefault();
      onType(event.key);
    }
  };

  function handlePaste(event: ClipboardEvent<HTMLTextAreaElement>) {
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

  useEffect(() => {
    terminalRef.current?.focus();
    inputRef.current?.focus();
    stickToBottomRef.current = true;
    if (outputRef.current) outputRef.current.scrollTop = outputRef.current.scrollHeight;
  }, [pty.sid]);

  useEffect(() => {
    const next = { rows: pty.rows || 30, cols: pty.cols || 120 };
    lastResizeRef.current = `${next.rows}x${next.cols}`;
    setTerminalSize(next);
  }, [pty.sid]);

  useEffect(() => {
    if (typeof ResizeObserver === 'undefined') return undefined;
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
  }, [pty.sid]);

  useEffect(() => {
    const output = outputRef.current;
    if (!output || !stickToBottomRef.current) return;
    output.scrollTop = output.scrollHeight;
  }, [displayLog]);

  return (
    <PaneShell>
      <PaneHeader
        eyebrow={`PTY ${pty.sid}`}
        title={pty.label}
        meta={`${pty.cwd} · ${pty.alive ? 'alive' : 'dead'} · ${ago(pty.last_output)}`}
        actions={
          <>
            <Button variant="outline" size="sm" onClick={onClose} loading={closeLoading} disabled={!!busy}>
              Close
            </Button>
            <Button variant="danger" size="sm" onClick={onDelete} loading={deleteLoading} disabled={!!busy}>
              Delete
            </Button>
          </>
        }
      />
      <div
        ref={terminalRef}
        tabIndex={-1}
        onClick={focusTerminal}
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
          autoFocus
          value=""
          aria-label="Terminal input"
          onChange={() => {}}
          onFocus={focusTerminal}
          onMouseDown={focusTerminal}
          onKeyDown={captureKeyDown}
          onPaste={handlePaste}
          onClick={focusTerminal}
          className="min-h-[40px] resize-none border-border/70 bg-background/75 font-mono text-[12px] text-foreground placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-primary/30"
          placeholder="Click here and type directly. Enter, Tab, arrows, Ctrl-C, paste all forward to the PTY."
        />
      </div>
      <div className="text-[11px] text-muted-foreground">
        offset {offset} · {alive ? 'streaming' : 'stopped'}
      </div>
    </PaneShell>
  );
}
