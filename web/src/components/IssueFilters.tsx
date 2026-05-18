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
    <div className="filter-row">
      {ISSUE_FILTERS.map((filter) => (
        <button
          key={filter.key}
          className={value === filter.key ? 'on' : ''}
          onClick={() => onChange(filter.key)}
        >
          {filter.label}
        </button>
      ))}
    </div>
  );
}
