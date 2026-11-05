import React from 'react';

export function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      {[1, 2, 3].map((n) => (
        <div
          key={n}
          className="bg-white rounded-3xl p-6 border border-rose-100 shadow-soft-sm animate-pulse space-y-4"
        >
          <div className="flex justify-between items-center">
            <div className="h-4 bg-slate-200 rounded w-1/3" />
            <div className="h-4 bg-slate-200 rounded w-1/6" />
          </div>
          <div className="flex gap-2">
            <div className="h-8 bg-slate-100 rounded-xl w-24" />
            <div className="h-8 bg-slate-100 rounded-xl w-32" />
            <div className="h-8 bg-slate-100 rounded-xl w-20" />
          </div>
          <div className="flex justify-between items-center pt-2">
            <div className="h-6 bg-slate-100 rounded w-1/4" />
            <div className="h-6 bg-rose-100 rounded w-20" />
          </div>
        </div>
      ))}
    </div>
  );
}
