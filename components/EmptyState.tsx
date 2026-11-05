import React from 'react';
import Link from 'next/link';
import { Compass, RotateCcw } from 'lucide-react';

interface EmptyStateProps {
  source: string;
  destination: string;
  onReset?: () => void;
}

export function EmptyState({ source, destination, onReset }: EmptyStateProps) {
  return (
    <div className="bg-white rounded-3xl p-10 border border-rose-100 shadow-soft-sm text-center max-w-lg mx-auto">
      <div className="w-16 h-16 rounded-2xl bg-rose-50 text-brand-800 flex items-center justify-center mx-auto mb-4 border border-rose-200 shadow-inner">
        <Compass size={32} />
      </div>

      <h3 className="text-lg font-bold text-slate-900 mb-1">
        No Direct Combinations Found
      </h3>

      <p className="text-xs text-slate-500 mb-6 leading-relaxed">
        We couldn&apos;t automatically compute a viable multimodal itinerary between{' '}
        <span className="font-semibold text-slate-800">&quot;{source}&quot;</span> and{' '}
        <span className="font-semibold text-slate-800">&quot;{destination}&quot;</span>. Try selecting a nearby transit hub or landmark.
      </p>

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
          >
            <RotateCcw size={14} />
            Reset to Popular Route
          </button>
        )}

        <Link
          href="/"
          className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-brand-800 hover:bg-brand-900 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-sm transition-colors"
        >
          Modify Search
        </Link>
      </div>
    </div>
  );
}
