import React from 'react';
import { RouteLeg } from '@/types/transit';
import { TransitIcon, getModeBadgeDetails } from '@/components/TransitIcon';
import { ShieldCheck, HelpCircle, ArrowRight, Database } from 'lucide-react';

interface RouteLegItemProps {
  leg: RouteLeg;
  isLast: boolean;
  stepNumber: number;
}

export function RouteLegItem({ leg, isLast, stepNumber }: RouteLegItemProps) {
  const badgeDetails = getModeBadgeDetails(leg.mode);
  const isZeroFare = leg.fare === 0;

  return (
    <div className="relative flex gap-4 text-xs">
      {/* Timeline Column */}
      <div className="flex flex-col items-center">
        <div
          className={`w-8 h-8 rounded-full flex items-center justify-center border shadow-sm ${badgeDetails.bgClass} ${badgeDetails.borderClass} ${badgeDetails.textClass}`}
        >
          <TransitIcon mode={leg.mode} size={15} />
        </div>
        {!isLast && (
          <div className="w-0.5 grow bg-slate-200 my-1 min-h-[36px]" />
        )}
      </div>

      {/* Content Column */}
      <div className="grow pb-6">
        <div className="bg-slate-50/70 border border-slate-200/80 rounded-2xl p-4 hover:bg-slate-50 transition-colors">
          {/* Header Row */}
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-slate-500 text-[11px]">
                Step {stepNumber}
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[11px] font-bold border ${badgeDetails.bgClass} ${badgeDetails.borderClass} ${badgeDetails.textClass}`}
              >
                {badgeDetails.label}
              </span>
              {leg.routeNumber && (
                <span className="font-bold text-slate-800 text-xs bg-white px-2 py-0.5 rounded-md border border-slate-200">
                  Route {leg.routeNumber}
                </span>
              )}
              {leg.serviceType && (
                <span className="text-slate-500 text-[11px] hidden sm:inline">
                  • {leg.serviceType}
                </span>
              )}
            </div>

            {/* Leg Fare & Verification Badge */}
            <div className="flex items-center gap-2">
              <div
                className={`font-bold px-2.5 py-1 rounded-lg text-xs flex items-center gap-1 ${
                  isZeroFare && leg.mode !== 'walking'
                    ? 'bg-rose-100 text-brand-900 border border-brand-200'
                    : isZeroFare
                    ? 'bg-slate-100 text-slate-600'
                    : leg.isVerified
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                    : 'bg-amber-50 text-amber-800 border border-amber-200'
                }`}
              >
                <span>₹{leg.fare}</span>
                {leg.isVerified ? (
                  <span title="Verified Official Government Rate">
                    <ShieldCheck size={13} className="text-emerald-700" />
                  </span>
                ) : (
                  <span title="Spatially Derived / Indicative Estimate">
                    <HelpCircle size={13} className="text-amber-600" />
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Stops / Trajectory (Exact Theme7 stop names) */}
          <div className="flex flex-col gap-1.5 my-2">
            <div className="flex items-center gap-2 text-slate-800 font-medium">
              <span className="w-2 h-2 rounded-full bg-brand-800 shrink-0" />
              <span className="font-semibold text-slate-900">{leg.fromStop}</span>
              <ArrowRight size={13} className="text-slate-400 shrink-0" />
              <span className="font-semibold text-slate-900">{leg.toStop}</span>
            </div>

            {leg.instructions && (
              <p className="text-slate-600 text-[11px] pl-4 italic">
                {leg.instructions}
              </p>
            )}
          </div>

          {/* Footer of leg: Duration, Distance, Notes & Data Provenance */}
          <div className="mt-3 pt-2.5 border-t border-slate-200/60 flex flex-wrap items-center justify-between gap-2 text-[11px] text-slate-500">
            <div className="flex items-center gap-3">
              <span>{leg.durationMinutes} mins</span>
              <span>•</span>
              <span>
                {leg.distanceMeters >= 1000
                  ? `${(leg.distanceMeters / 1000).toFixed(1)} km`
                  : `${leg.distanceMeters} m`}
              </span>
              {leg.isVerified ? (
                <span className="text-emerald-700 font-semibold bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  Official Rate
                </span>
              ) : (
                <span className="text-amber-700 font-medium bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  Derived / Estimated
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {leg.fareNote && (
                <span className="font-medium text-slate-700">{leg.fareNote}</span>
              )}
              {leg.provenance && (
                <span className="text-[10px] text-slate-400 font-mono flex items-center gap-1 bg-white px-1.5 py-0.5 rounded border border-slate-200" title={`Dataset Provenance: ${leg.provenance}`}>
                  <Database size={10} className="text-slate-400" />
                  {leg.provenance.replace('Theme7.', '').replace('Public_Transport.', '')}
                </span>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
