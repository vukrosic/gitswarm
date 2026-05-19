import type { ReactNode } from 'react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

const TONE_BY_LABEL: Record<string, 'success' | 'warning' | 'destructive'> = {
  ok: 'success',
  'claim-next': 'success',
  pending: 'warning',
  'in-progress': 'warning',
  fail: 'destructive',
  missing: 'destructive',
};

export function chipVariant(label: string): 'default' | 'success' | 'warning' | 'destructive' {
  return TONE_BY_LABEL[label] ?? 'default';
}

export function PaneShell({ className, children }: { className?: string; children: ReactNode }) {
  return (
    <section
      className={cn(
        'scrollbar-thin flex min-h-full flex-col gap-3.5 overflow-auto rounded-[var(--radius)] border border-border bg-gradient-to-b from-card/90 to-background/95 p-5 shadow-[0_24px_70px_hsl(0_0%_0%/0.42)] backdrop-blur-xl',
        className,
      )}
    >
      {children}
    </section>
  );
}

export function PaneHeader({
  eyebrow,
  title,
  meta,
  chips,
  ciChips,
  actions,
}: {
  eyebrow: string;
  title: string;
  meta?: ReactNode;
  chips?: string[];
  ciChips?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-start justify-between gap-4 border-b border-border/60 pb-3">
      <div className="min-w-0">
        <div className="text-[10px] font-medium uppercase tracking-[0.18em] text-muted-foreground">{eyebrow}</div>
        <h2 className="mt-1 text-xl font-semibold leading-tight tracking-tight text-foreground">{title}</h2>
        {meta ? <div className="mt-1.5 text-[11px] text-muted-foreground">{meta}</div> : null}
        <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
          {chips && chips.length ? chips.map((label) => (
            <Badge key={label} variant={chipVariant(label)}>
              {label}
            </Badge>
          )) : null}
          {ciChips}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center justify-end gap-1.5">{actions}</div> : null}
    </header>
  );
}
