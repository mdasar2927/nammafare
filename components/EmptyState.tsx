import React from 'react';
import Link from 'next/link';
import { Compass, RotateCcw, MapPinOff } from 'lucide-react';

interface EmptyStateProps {
  source: string;
  destination: string;
  message?: string | null;
  originTaz?: string | null;
  destTaz?: string | null;
  onReset?: () => void;
}

export function EmptyState({
  source,
  destination,
  message,
  originTaz,
  destTaz,
  onReset,
}: EmptyStateProps) {
  return (
    <div className="bg-white rounded-3xl p-8 sm:p-10 border border-rose-100 shadow-soft-sm text-center max-w-lg mx-auto">
      <div className="w-16 h-16 rounded-2xl bg-rose-50 text-brand-800 flex items-center justify-center mx-auto mb-4 border border-rose-200 shadow-inner">
        <MapPinOff size={32} />
      </div>

      <h3 className="text-lg font-bold text-slate-900 mb-2">
        No Connected Transit Route Found
      </h3>

      <p className="text-xs text-slate-600 mb-4 leading-relaxed">
        {message ||
          `No connected public transport route could be traced in the Theme7 Chennai transit network between "${source}" and "${destination}".`}
      </p>

      {(originTaz || destTaz) && (
        <div className="mb-6 p-2.5 rounded-xl bg-slate-50 border border-slate-200 text-[11px] text-slate-500 flex items-center justify-center gap-3 font-mono">
          {originTaz && <span>Origin TAZ: {originTaz}</span>}
          {originTaz && destTaz && <span>•</span>}
          {destTaz && <span>Destination TAZ: {destTaz}</span>}
        </div>
      )}

      <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            className="w-full sm:w-auto px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold flex items-center justify-center gap-1.5 transition-colors"
          >
            <RotateCcw size={14} />
            Try Connected Corridor
          </button>
        )}

        <Link
          href="/"
          className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-brand-800 hover:bg-brand-900 text-white text-xs font-semibold flex items-center justify-center gap-1.5 shadow-sm transition-colors"
        >
          Modify Locations
        </Link>
      </div>
    </div>
  );
}
