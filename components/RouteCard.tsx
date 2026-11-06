'use client';

import React, { useState } from 'react';
import { MultimodalRoute, Gender } from '@/types/transit';
import {
  ChevronDown,
  Clock,
  ArrowRight,
  Bus,
  Footprints,
  Train,
  TrainFront,
  MapPin,
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

  return (
    <div
      className={`bg-white rounded-2xl border transition-all duration-300 cursor-pointer animate-stagger-3 group ${
        isExpanded
          ? 'border-rose-200 shadow-md'
          : 'border-slate-200 shadow-sm hover:border-slate-300 hover:shadow-md'
      }`}
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <div className="p-6">
        {/* Top Badges & Expand Arrow */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex flex-wrap items-center gap-2">
            {route.highlightBadge === 'Cheapest' && (
              <span className="bg-emerald-50 text-emerald-700 border border-emerald-100 px-2.5 py-1 rounded-lg text-xs font-semibold">
                Lowest Fare
              </span>
            )}
            {route.highlightBadge === 'Fastest' && (
              <span className="bg-sky-50 text-sky-700 border border-sky-100 px-2.5 py-1 rounded-lg text-xs font-semibold">
                Fastest ETA
              </span>
            )}
            <span className="bg-slate-100 text-slate-600 border border-slate-200 px-2.5 py-1 rounded-lg text-xs font-medium">
              {route.isVerified ? 'Official Fare' : 'Derived Route'}
            </span>
            {hasVidiyalBenefit && (
              <span className="bg-rose-50 text-rose-700 border border-rose-100 px-2.5 py-1 rounded-lg text-xs font-semibold">
                Vidiyal Scheme (₹0 MTC)
              </span>
            )}
          </div>
          <div
            className={`p-1.5 rounded-full transition-transform duration-300 ${
              isExpanded
                ? 'rotate-180 bg-slate-100 text-slate-800'
                : 'bg-slate-50 text-slate-400 group-hover:bg-slate-100 group-hover:text-slate-800'
            }`}
          >
            <ChevronDown size={20} />
          </div>
        </div>

        {/* Content: Summary, Visual Path, Duration & Fare */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <h3 className="text-xl font-bold text-slate-900 mb-3">{route.summary}</h3>

            {/* Visual Path */}
            <div className="flex flex-wrap items-center gap-3 text-sm font-medium">
              {route.legs.map((leg, idx) => (
                <React.Fragment key={leg.id || idx}>
                  {leg.mode === 'walking' ? (
                    <div className="flex items-center gap-1.5 text-slate-600 bg-slate-50 px-3 py-1.5 rounded-xl border border-slate-100">
                      <Footprints size={16} /> {leg.durationMinutes}m
                    </div>
                  ) : leg.mode === 'mtc_bus' ? (
                    <div className="flex items-center gap-1.5 text-rose-700 bg-rose-50 px-3 py-1.5 rounded-xl border border-rose-100">
                      <Bus size={16} /> {leg.durationMinutes}m
                    </div>
                  ) : leg.mode === 'metro' ? (
                    <div className="flex items-center gap-1.5 text-sky-700 bg-sky-50 px-3 py-1.5 rounded-xl border border-sky-100">
                      <Train size={16} /> {leg.durationMinutes}m
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5 text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-xl border border-indigo-100">
                      <TrainFront size={16} /> {leg.durationMinutes}m
                    </div>
                  )}
                  {idx < route.legs.length - 1 && (
                    <ArrowRight size={14} className="text-slate-300" />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-8 md:text-right shrink-0 bg-slate-50 md:bg-transparent p-4 md:p-0 rounded-xl">
            <div>
              <div className="flex items-center gap-1.5 text-slate-400 text-xs font-medium uppercase tracking-wider mb-1 md:justify-end">
                <Clock size={14} /> Duration
              </div>
              <div className="text-2xl font-bold text-slate-800">
                {route.totalDurationMinutes}
                <span className="text-sm font-medium text-slate-500 ml-1">mins</span>
              </div>
            </div>
            <div className="w-px h-10 bg-slate-200 md:hidden"></div>
            <div>
              <div className="text-slate-400 text-xs font-medium uppercase tracking-wider mb-1 md:justify-end">
                Total Fare
              </div>
              <div className="text-2xl font-bold text-rose-600">
                ₹{route.calculatedTotalFare}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-t border-slate-100 bg-slate-50/50 p-6 rounded-b-2xl animate-details">
          <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-6">
            Step-by-Step Itinerary
          </h4>

          <div className="relative pl-6 border-l-2 border-slate-200 flex flex-col gap-8 ml-2">
            {route.legs.map((leg, index) => {
              const isWalking = leg.mode === 'walking';
              const isBus = leg.mode === 'mtc_bus';
              const isMetro = leg.mode === 'metro';

              let legTitle = '';
              if (isWalking) {
                legTitle = `Walk to ${leg.toStop}`;
              } else if (isBus) {
                legTitle = `Board MTC Route ${leg.routeNumber || leg.serviceType || 'Bus'}`;
              } else if (isMetro) {
                legTitle = `Board Chennai Metro: ${leg.serviceType || 'Metro Rail'}`;
              } else {
                legTitle = `Board Southern Railway: ${leg.serviceType || 'Suburban Train'}`;
              }

              return (
                <div key={leg.id || index} className="relative">
                  <div
                    className={`absolute top-0 bg-white border-2 rounded-full ${
                      isWalking
                        ? 'border-slate-200 text-slate-500 p-1.5 -left-[1.85rem]'
                        : isBus
                        ? 'border-rose-200 text-rose-500 p-2 -left-[1.95rem]'
                        : isMetro
                        ? 'border-sky-200 text-sky-500 p-2 -left-[1.95rem]'
                        : 'border-indigo-200 text-indigo-500 p-2 -left-[1.95rem]'
                    }`}
                  >
                    {isWalking && <Footprints size={16} />}
                    {isBus && <Bus size={18} />}
                    {isMetro && <Train size={18} />}
                    {!isWalking && !isBus && !isMetro && <TrainFront size={18} />}
                  </div>
                  <div className="-mt-1">
                    <div className="flex items-center justify-between mb-1">
                      <h5 className="font-semibold text-slate-800">{legTitle}</h5>
                      <span
                        className={`text-sm font-medium px-2 py-0.5 rounded ${
                          leg.fare === 0
                            ? 'text-emerald-600 bg-emerald-50'
                            : 'text-rose-700 bg-rose-50 border border-rose-100'
                        }`}
                      >
                        ₹{leg.fare} {leg.isVerified ? 'Official' : ''}
                      </span>
                    </div>
                    <p className="text-sm text-slate-500 mb-2">
                      {leg.fromStop} <ArrowRight size={12} className="inline mx-1" /> {leg.toStop}
                    </p>
                    <span className="text-xs text-slate-400 bg-white border border-slate-200 px-2 py-1 rounded-md">
                      {leg.durationMinutes} mins
                      {leg.distanceMeters > 0 ? ` • ${leg.distanceMeters}m` : ''}
                    </span>
                  </div>
                </div>
              );
            })}

            {/* Final Destination Step */}
            <div className="relative">
              <div className="absolute -left-[1.85rem] top-0 bg-white border-2 border-slate-200 text-rose-600 p-1.5 rounded-full">
                <MapPin size={16} />
              </div>
              <div className="-mt-1">
                <h5 className="font-semibold text-slate-800">Arrive at Destination</h5>
                <p className="text-sm text-slate-500 mt-1">{route.destination}</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
