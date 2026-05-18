import type { FileEntry } from '../types';
import { fmtTime } from '../lib/time';
import { PaneHeader, PaneShell } from './_shared';

interface FilePaneProps {
  file: FileEntry;
  text: string;
}

export function FilePane({ file, text }: FilePaneProps) {
  return (
    <PaneShell>
      <PaneHeader
        eyebrow="State file"
        title={file.name}
        meta={`${Math.round(file.size / 1024)} KB · ${fmtTime(file.mtime)}`}
      />
      <pre className="scrollbar-thin m-0 min-h-0 flex-1 overflow-auto whitespace-pre-wrap rounded-2xl border border-border bg-background/80 p-4 font-mono text-[12px] leading-relaxed text-foreground shadow-[inset_0_1px_0_hsl(0_0%_100%/0.03)]">
        {text || 'Loading file...'}
      </pre>
    </PaneShell>
  );
}
