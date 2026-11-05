import React from 'react';
import { SortPreference } from '@/types/transit';
import { IndianRupee, Clock } from 'lucide-react';

interface SortToggleProps {
  sortBy: SortPreference;
  onChange: (sort: SortPreference) => void;
  size?: 'sm' | 'md';
}

export function SortToggle({ sortBy, onChange, size = 'md' }: SortToggleProps) {
  const isSm = size === 'sm';

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-semibold text-slate-700 tracking-wide uppercase">
        Route Preference
      </label>

      <div className="inline-flex p-1 bg-slate-100/90 rounded-xl border border-slate-200/80 w-full sm:w-auto">
        <button
          type="button"
          onClick={() => onChange('cost')}
          className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all duration-200 ${
            isSm ? 'px-3 py-1 text-xs' : 'px-4 py-2 text-sm'
          } ${
            sortBy === 'cost'
              ? 'bg-brand-900 text-white shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          aria-pressed={sortBy === 'cost'}
        >
          <IndianRupee size={isSm ? 13 : 15} />
          <span>Lowest Cost</span>
        </button>

        <button
          type="button"
          onClick={() => onChange('time')}
          className={`flex-1 sm:flex-none flex items-center justify-center gap-1.5 rounded-lg font-medium transition-all duration-200 ${
            isSm ? 'px-3 py-1 text-xs' : 'px-4 py-2 text-sm'
          } ${
            sortBy === 'time'
              ? 'bg-brand-900 text-white shadow-sm font-semibold'
              : 'text-slate-600 hover:text-slate-900'
          }`}
          aria-pressed={sortBy === 'time'}
        >
          <Clock size={isSm ? 13 : 15} />
          <span>Least Time</span>
        </button>
      </div>
    </div>
  );
}
