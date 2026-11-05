'use client';

import React, { useState } from 'react';
import { MultimodalRoute, Gender } from '@/types/transit';
import { RouteLegItem } from '@/components/RouteLegItem';
import { TransitIcon, getModeBadgeDetails } from '@/components/TransitIcon';
import {
  ChevronDown,
  ChevronUp,
  Clock,
  IndianRupee,
  ShieldCheck,
  HelpCircle,
  Sparkles,
  ArrowRight,
  TrendingDown,
  Zap,
} from 'lucide-react';

interface RouteCardProps {
  route: MultimodalRoute;
  currentGender: Gender;
  isInitiallyExpanded?: boolean;
}

export function RouteCard({
  route,
  currentGender,
  isInitiallyExpanded = false,
}: RouteCardProps) {
  const [isExpanded, setIsExpanded] = useState(isInitiallyExpanded);

  // Check if any leg benefits from Vidiyal scheme
  const hasVidiyalBenefit =
    currentGender === 'female' &&
    route.legs.some((l) => l.isVidiyalEligible);

  // Verified vs Estimated status
  const allVerified = route.hasVerifiedFaresOnly;

  return (
    <div
      className={`bg-white rounded-3xl border transition-all duration-200 overflow-hidden ${
        isExpanded
          ? 'border-brand-700/40 shadow-soft-lg ring-1 ring-brand-700/10'
          : 'border-rose-100/90 shadow-soft-sm hover:shadow-soft-md hover:border-brand-300'
      }`}
    >
      {/* Top Banner (Optional Highlight) */}
      <div className="flex items-center justify-between px-6 pt-4 pb-2 border-b border-slate-100 bg-gradient-to-r from-rose-50/40 via-white to-transparent">
        <div className="flex items-center gap-2">
          {route.highlightBadge === 'Cheapest' && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
              <TrendingDown size={13} />
              Lowest Fare
            </span>
          )}
          {route.highlightBadge === 'Fastest' && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-sky-100 text-sky-800 border border-sky-200">
              <Zap size={13} />
              Fastest ETA
            </span>
          )}
          {route.highlightBadge === 'Balanced' && (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-100 text-purple-800 border border-purple-200">
              <Sparkles size={13} />
              Recommended
            </span>
          )}

          {allVerified ? (
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200">
              <ShieldCheck size={12} />
              100% Verified Official Fares
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-200">
              <HelpCircle size={12} />
              Includes Calibrated Estimates
            </span>
          )}
        </div>

        {hasVidiyalBenefit && (
          <span className="inline-flex items-center gap-1 text-[11px] font-bold text-brand-900 bg-rose-100/80 px-2.5 py-0.5 rounded-full border border-brand-200 animate-pulse">
            <Sparkles size={12} className="text-brand-600" />
            Vidiyal Scheme Applied (₹0 MTC)
          </span>
        )}
      </div>

      {/* Main Card Summary (Click to expand) */}
      <button
        type="button"
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full text-left p-6 flex flex-col md:flex-row md:items-center justify-between gap-6 cursor-pointer focus:outline-none"
        aria-expanded={isExpanded}
      >
        {/* Left Column: Summary & Mode Sequence */}
        <div className="flex-1 space-y-3">
          <div className="space-y-1">
            <h3 className="font-bold text-slate-900 text-base sm:text-lg group-hover:text-brand-900 transition-colors">
              {route.summary}
            </h3>
            <p className="text-xs text-slate-500">
              {route.transfersCount === 0
                ? 'Direct Route • No Transfers'
                : `${route.transfersCount} Transit Transfer${
                    route.transfersCount > 1 ? 's' : ''
                  }`}
            </p>
          </div>

          {/* Mode Pill Flow */}
          <div className="flex flex-wrap items-center gap-2 pt-1">
            {route.legs.map((leg, idx) => {
              const details = getModeBadgeDetails(leg.mode);
              return (
                <React.Fragment key={leg.id}>
                  <div
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-xl text-xs font-semibold border ${details.bgClass} ${details.borderClass} ${details.textClass}`}
                  >
                    <TransitIcon mode={leg.mode} size={14} />
                    <span>
                      {leg.routeNumber || details.label}
                    </span>
                    <span className="text-[10px] opacity-75 font-normal">
                      ({leg.durationMinutes}m)
                    </span>
                  </div>

                  {idx < route.legs.length - 1 && (
                    <ArrowRight size={13} className="text-slate-300 shrink-0" />
                  )}
                </React.Fragment>
              );
            })}
          </div>
        </div>

        {/* Right Column: Fare, Duration & Toggle */}
        <div className="flex items-center justify-between md:justify-end gap-6 pt-3 md:pt-0 border-t md:border-t-0 border-slate-100">
          {/* Duration */}
          <div className="text-left md:text-right">
            <div className="text-xs font-medium text-slate-500 flex items-center md:justify-end gap-1">
              <Clock size={13} />
              <span>Duration</span>
            </div>
            <div className="font-black text-slate-900 text-lg sm:text-xl">
              {route.totalDurationMinutes}{' '}
              <span className="text-xs font-semibold text-slate-500">mins</span>
            </div>
          </div>

          {/* Total Fare */}
          <div className="text-left md:text-right min-w-[90px]">
            <div className="text-xs font-medium text-slate-500 flex items-center md:justify-end gap-1">
              <IndianRupee size={13} />
              <span>Total Fare</span>
            </div>
            <div className="font-black text-xl sm:text-2xl text-brand-900 flex items-center md:justify-end">
              <span>₹{route.calculatedTotalFare}</span>
            </div>
          </div>

          {/* Expand Chevron */}
          <div className="w-10 h-10 rounded-full bg-slate-50 border border-slate-200/80 flex items-center justify-center text-slate-600 hover:text-brand-900 hover:bg-rose-50 transition-colors shrink-0">
            {isExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </div>
        </div>
      </button>

      {/* Expanded Step-by-Step Breakdown */}
      {isExpanded && (
        <div className="px-6 pb-6 pt-2 border-t border-slate-100 bg-slate-50/30">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-bold text-slate-700 tracking-wider uppercase">
              Step-by-Step Itinerary & Fare Breakdown
            </span>
            <span className="text-xs text-slate-500">
              Click to collapse
            </span>
          </div>

          <div className="space-y-0">
            {route.legs.map((leg, index) => (
              <RouteLegItem
                key={leg.id}
                leg={leg}
                stepNumber={index + 1}
                isLast={index === route.legs.length - 1}
              />
            ))}
          </div>

          {/* Disclaimers & Notes */}
          <div className="mt-4 p-3 rounded-xl bg-white border border-rose-100 text-[11px] text-slate-500 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-emerald-600 shrink-0" />
              <span>
                Verified government transit fares reflect official Southern Railway, CMRL, and MTC Chennai rate charts.
              </span>
            </div>
            <span className="text-[10px] text-slate-400 font-mono">
              ID: {route.id}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
