import { cn } from '@/lib/utils';
import type { IssueFilter } from '../types/dashboard';

export const ISSUE_FILTERS: Array<{ key: IssueFilter; label: string }> = [
  { key: 'all', label: 'All' },
  { key: 'claim-next', label: 'Claim next' },
  { key: 'good first issue', label: 'Good first' },
  { key: 'agent-friendly', label: 'Agent' },
  { key: 'needs-validation', label: 'Validation' },
  { key: 'parked', label: 'Parked' },
];

interface IssueFiltersProps {
  value: IssueFilter;
  onChange: (value: IssueFilter) => void;
}

export function IssueFilters({ value, onChange }: IssueFiltersProps) {
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pt-3">
      {ISSUE_FILTERS.map((filter) => {
        const active = value === filter.key;
        return (
          <button
            key={filter.key}
            type="button"
            onClick={() => onChange(filter.key)}
            className={cn(
              'rounded-full border px-2.5 py-1 text-[11px] font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
              active
                ? 'border-primary/60 bg-gradient-to-b from-primary/15 to-primary/5 text-foreground'
                : 'border-border bg-card/40 text-muted-foreground hover:border-primary/40 hover:text-foreground',
            )}
          >
            {filter.label}
          </button>
        );
      })}
    </div>
  );
}
