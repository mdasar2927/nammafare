'use client';

import React, { Suspense, useState, useEffect, useMemo } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Navigation,
  MapPin,
  ArrowUpDown,
  RotateCcw,
  Sparkles,
  ArrowLeft,
  SlidersHorizontal,
  Info,
  ShieldCheck,
  Compass,
} from 'lucide-react';
import { Gender, SortPreference, MultimodalRoute } from '@/types/transit';
import { SAMPLE_MULTIMODAL_ROUTES } from '@/data/mockRoutes';
import { processRoutes } from '@/lib/fareEngine';
import { RouteCard } from '@/components/RouteCard';
import { GenderToggle } from '@/components/GenderToggle';
import { SortToggle } from '@/components/SortToggle';
import { LoadingSkeleton } from '@/components/LoadingSkeleton';
import { EmptyState } from '@/components/EmptyState';

function RoutesContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Read URL query parameters
  const initialSource = searchParams.get('source') || 'Chennai Central (Puratchi Thalaivar Dr. M.G.R.)';
  const initialDestination = searchParams.get('destination') || 'Guindy';
  const initialGender = (searchParams.get('gender') as Gender) || 'male';
  const initialSort = (searchParams.get('sort') as SortPreference) || 'cost';

  // State
  const [source, setSource] = useState(initialSource);
  const [destination, setDestination] = useState(initialDestination);
  const [gender, setGender] = useState<Gender>(initialGender);
  const [sortBy, setSortBy] = useState<SortPreference>(initialSort);
  const [isLoading, setIsLoading] = useState(false);

  // Sync state if URL changes
  useEffect(() => {
    if (searchParams.get('source')) setSource(searchParams.get('source')!);
    if (searchParams.get('destination')) setDestination(searchParams.get('destination')!);
    if (searchParams.get('gender')) setGender(searchParams.get('gender') as Gender);
    if (searchParams.get('sort')) setSortBy(searchParams.get('sort') as SortPreference);
  }, [searchParams]);

  // Update URL search parameters when interactive controls change (without full reload)
  const updateUrlParams = (newGender: Gender, newSort: SortPreference, newSrc = source, newDst = destination) => {
    const params = new URLSearchParams({
      source: newSrc,
      destination: newDst,
      gender: newGender,
      sort: newSort,
    });
    router.replace(`/routes?${params.toString()}`, { scroll: false });
  };

  const handleGenderChange = (newGender: Gender) => {
    setGender(newGender);
    updateUrlParams(newGender, sortBy);
  };

  const handleSortChange = (newSort: SortPreference) => {
    setSortBy(newSort);
    updateUrlParams(gender, newSort);
  };

  const handleSwap = () => {
    const tempSrc = source;
    const tempDst = destination;
    setSource(tempDst);
    setDestination(tempSrc);
    setIsLoading(true);
    setTimeout(() => setIsLoading(false), 250);
    updateUrlParams(gender, sortBy, tempDst, tempSrc);
  };

  // Dynamically recalculate and sort routes
  const processedRoutes: MultimodalRoute[] = useMemo(() => {
    // Generate route copies adjusted to source and destination
    const baseRoutes = SAMPLE_MULTIMODAL_ROUTES.map((r) => ({
      ...r,
      source,
      destination,
    }));

    return processRoutes(baseRoutes, gender, sortBy);
  }, [source, destination, gender, sortBy]);

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-12">
      {/* Back button & Breadcrumbs */}
      <div className="flex items-center justify-between mb-6">
        <Link
          href="/"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-brand-900 transition-colors bg-white px-3 py-1.5 rounded-xl border border-slate-200 shadow-soft-sm"
        >
          <ArrowLeft size={14} />
          <span>Back to Search</span>
        </Link>

        <div className="text-[11px] font-semibold text-brand-900 bg-rose-50 px-3 py-1 rounded-full border border-rose-200 flex items-center gap-1.5">
          <Compass size={13} className="text-brand-700" />
          <span>Chennai Multimodal Engine</span>
        </div>
      </div>

      {/* Top Bar: Journey Overview & Editable Controls */}
      <div className="bg-white rounded-3xl p-6 sm:p-7 border border-rose-100 shadow-soft-lg mb-8">
        <div className="grid grid-cols-1 lg:grid-cols-[1.2fr,auto,1.5fr] gap-6 items-center">
          {/* Origin & Destination Display with Quick Swap */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <div className="flex-1 space-y-1">
              <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                Origin
              </div>
              <div className="flex items-center gap-2 text-slate-900 font-bold text-sm sm:text-base">
                <Navigation size={16} className="text-rose-600 shrink-0 transform rotate-45" />
                <span className="truncate">{source}</span>
              </div>
            </div>

            <button
              type="button"
              onClick={handleSwap}
              title="Swap origin and destination"
              className="w-9 h-9 rounded-full bg-rose-50 hover:bg-rose-100 border border-rose-200 text-brand-900 flex items-center justify-center transition-all hover:rotate-180 duration-300 self-center shrink-0 shadow-sm"
            >
              <ArrowUpDown size={15} />
            </button>

            <div className="flex-1 space-y-1">
              <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400">
                Destination
              </div>
              <div className="flex items-center gap-2 text-slate-900 font-bold text-sm sm:text-base">
                <MapPin size={16} className="text-brand-800 shrink-0" />
                <span className="truncate">{destination}</span>
              </div>
            </div>
          </div>

          <div className="hidden lg:block w-px h-12 bg-slate-200" />

          {/* Editable Controls: Sort Preference & Commuter Profile (Gender) */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
            <div className="flex-1">
              <SortToggle sortBy={sortBy} onChange={handleSortChange} size="sm" />
            </div>
            <div className="flex-1">
              <GenderToggle
                gender={gender}
                onChange={handleGenderChange}
                size="sm"
                showHelpText={false}
              />
            </div>
          </div>
        </div>

        {/* Dynamic Status / Banner notice */}
        <div className="mt-5 pt-4 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-600">
            <SlidersHorizontal size={14} className="text-slate-400" />
            <span>
              Showing <span className="font-bold text-slate-900">{processedRoutes.length}</span> multimodal options sorted by{' '}
              <span className="font-bold text-brand-900">{sortBy === 'cost' ? 'Lowest Cost (₹)' : 'Least Time (mins)'}</span>.
            </span>
          </div>

          {gender === 'female' ? (
            <div className="inline-flex items-center gap-1.5 text-brand-900 bg-rose-50 px-3 py-1 rounded-lg border border-rose-200 font-semibold text-[11px]">
              <Sparkles size={13} className="text-brand-600" />
              <span>Vidiyal Payana Thittam Active: Ordinary MTC Buses are ₹0</span>
            </div>
          ) : (
            <div className="inline-flex items-center gap-1.5 text-slate-500 text-[11px]">
              <Info size={13} className="text-slate-400" />
              <span>Standard MTC stage fares applied for male commuters</span>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="space-y-6">
        {/* Results Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <span>Viable Chennai Routes</span>
            <span className="text-xs font-normal text-slate-500">
              (Click any card to expand step-by-step breakdown)
            </span>
          </h2>

          <div className="text-xs text-slate-500 hidden sm:flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
            <span>Verified Fare</span>
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 ml-2" />
            <span>Calibrated Estimate</span>
          </div>
        </div>

        {/* Routes List or Loading / Empty States */}
        {isLoading ? (
          <LoadingSkeleton />
        ) : processedRoutes.length === 0 ? (
          <EmptyState
            source={source}
            destination={destination}
            onReset={() => {
              setSource('Chennai Central (Puratchi Thalaivar Dr. M.G.R.)');
              setDestination('Guindy');
            }}
          />
        ) : (
          <div className="space-y-4">
            {processedRoutes.map((route, index) => (
              <RouteCard
                key={route.id}
                route={route}
                currentGender={gender}
                isInitiallyExpanded={index === 0} // Expand first card by default
              />
            ))}
          </div>
        )}

        {/* Transparency & Disclaimer Box */}
        <div className="bg-slate-50/80 rounded-2xl p-5 border border-slate-200/80 text-xs text-slate-600 space-y-2 mt-10">
          <div className="flex items-center gap-2 font-bold text-slate-800">
            <ShieldCheck size={16} className="text-brand-800" />
            <span>Chennai Transit Transparency & Rate Verification Notice</span>
          </div>
          <p className="leading-relaxed text-slate-500">
            • <strong>Verified Fares:</strong> Suburban train fares are calculated using official Indian Railways unreserved 2nd class distance slabs. CMRL fares are based on Chennai Metro Rail published distance slabs (with QR discount factor). MTC Bus fares correspond to Tamil Nadu State Transport ordinary and deluxe stage charts.
          </p>
          <p className="leading-relaxed text-slate-500">
            • <strong>Calibrated Estimates:</strong> Chennai auto rickshaws, share autos, and cab fares represent calibrated daytime market averages and are labeled accordingly. Real-time driver negotiations, wait times, or ride-hailing surge rates may vary.
          </p>
        </div>
      </div>
    </div>
  );
}

export default function RoutesPage() {
  return (
    <Suspense fallback={<div className="max-w-6xl mx-auto px-4 py-16"><LoadingSkeleton /></div>}>
      <RoutesContent />
    </Suspense>
  );
}
