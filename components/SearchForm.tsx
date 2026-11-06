'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowUpDown, Search, Navigation } from 'lucide-react';
import { Gender, SortPreference } from '@/types/transit';
import { resolveCoordinates } from '@/lib/api';
import { LocationInput } from '@/components/LocationInput';

export function SearchForm() {
  const router = useRouter();

  // Fresh homepage visit starts with both origin and destination empty and no coordinates
  const [source, setSource] = useState('');
  const [sourceCoords, setSourceCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [sourceType, setSourceType] = useState<string | undefined>(undefined);

  const [destination, setDestination] = useState('');
  const [destCoords, setDestCoords] = useState<{ lat: number; lng: number } | null>(null);
  const [destType, setDestType] = useState<string | undefined>(undefined);

  const [gender, setGender] = useState<Gender>('male'); // 'male' = General, 'female' = Women scheme
  const [sortBy, setSortBy] = useState<SortPreference>('cost'); // 'cost' = Lowest Cost, 'time' = Least Time

  // Form is valid only after both locations have non-empty text and resolved coordinates
  const isFormValid = Boolean(
    source.trim() &&
    destination.trim() &&
    sourceCoords &&
    typeof sourceCoords.lat === 'number' &&
    typeof sourceCoords.lng === 'number' &&
    destCoords &&
    typeof destCoords.lat === 'number' &&
    typeof destCoords.lng === 'number'
  );

  const handleSourceChange = (
    val: string,
    coords: { lat: number; lng: number } | null,
    type?: string
  ) => {
    setSource(val);
    setSourceCoords(coords);
    setSourceType(type);
  };

  const handleDestChange = (
    val: string,
    coords: { lat: number; lng: number } | null,
    type?: string
  ) => {
    setDestination(val);
    setDestCoords(coords);
    setDestType(type);
  };

  const swapLocations = () => {
    const tempSrc = source;
    const tempCoords = sourceCoords;
    const tempType = sourceType;

    setSource(destination);
    setSourceCoords(destCoords);
    setSourceType(destType);

    setDestination(tempSrc);
    setDestCoords(tempCoords);
    setDestType(tempType);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid || !sourceCoords || !destCoords) return;

    const params = new URLSearchParams({
      source: source.trim(),
      destination: destination.trim(),
      gender,
      sort: sortBy,
      sLat: sourceCoords.lat.toString(),
      sLng: sourceCoords.lng.toString(),
      dLat: destCoords.lat.toString(),
      dLng: destCoords.lng.toString(),
    });

    router.push(`/routes?${params.toString()}`);
  };

  const selectPopularRoute = async (src: string, dst: string) => {
    setSource(src);
    setDestination(dst);
    setSourceType('Theme7 Stop');
    setDestType('Theme7 Stop');

    try {
      const p1 = await resolveCoordinates(src);
      if (p1) setSourceCoords(p1);
      const p2 = await resolveCoordinates(dst);
      if (p2) setDestCoords(p2);
    } catch {
      // ignore
    }
  };

  return (
    <div className="w-full flex flex-col items-center">
      {/* Central Search Card */}
      <div className="w-full max-w-2xl bg-white p-6 sm:p-8 rounded-[2rem] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.05)] border border-slate-100 relative">
        <form onSubmit={handleSubmit}>
          {/* Inputs Section */}
          <div className="relative flex flex-col gap-3 mb-8">
            {/* Visual connector line between icons */}
            <div className="absolute left-[1.35rem] top-10 bottom-10 w-0.5 bg-slate-100 z-0 pointer-events-none" />

            {/* Starting Point Input */}
            <LocationInput
              id="start-point"
              iconType="origin"
              placeholder="Starting Point (Origin)"
              value={source}
              coords={sourceCoords}
              sourceType={sourceType}
              onChange={handleSourceChange}
            />

            {/* Swap Button */}
            <div className="absolute left-[0.8rem] top-1/2 -translate-y-1/2 z-20 flex justify-center w-8">
              <button
                type="button"
                onClick={swapLocations}
                className="bg-white p-1.5 rounded-full border border-slate-200 shadow-sm text-slate-400 hover:text-rose-600 hover:border-rose-200 transition-all active:scale-95 hover:rotate-180 duration-300"
                title="Swap locations"
              >
                <ArrowUpDown size={14} strokeWidth={2.5} />
              </button>
            </div>

            {/* Destination Input */}
            <LocationInput
              id="destination-point"
              iconType="destination"
              placeholder="Destination (Arrival)"
              value={destination}
              coords={destCoords}
              sourceType={destType}
              onChange={handleDestChange}
            />
          </div>

          {/* Options / Segmented Controls */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
            {/* Route Preference */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold text-slate-400 tracking-wider uppercase ml-1">
                Route Preference
              </label>
              <div className="bg-slate-100/80 p-1.5 rounded-2xl flex border border-slate-100">
                <button
                  type="button"
                  onClick={() => setSortBy('cost')}
                  className={`flex-1 py-2.5 px-4 text-sm font-semibold rounded-xl transition-all ${
                    sortBy === 'cost'
                      ? 'bg-white text-slate-800 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.1)]'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'
                  }`}
                >
                  ₹ Lowest Cost
                </button>
                <button
                  type="button"
                  onClick={() => setSortBy('time')}
                  className={`flex-1 py-2.5 px-4 text-sm font-semibold rounded-xl transition-all ${
                    sortBy === 'time'
                      ? 'bg-white text-slate-800 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.1)]'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'
                  }`}
                >
                  ⏱ Least Time
                </button>
              </div>
            </div>

            {/* Commuter Profile */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold text-slate-400 tracking-wider uppercase ml-1 flex justify-between items-center">
                <span>Commuter Profile</span>
                <span className="text-[10px] text-rose-500 font-medium capitalize bg-rose-50 px-2 py-0.5 rounded-full border border-rose-100">
                  Women Free Scheme
                </span>
              </label>
              <div className="bg-slate-100/80 p-1.5 rounded-2xl flex border border-slate-100">
                <button
                  type="button"
                  onClick={() => setGender('male')}
                  className={`flex-1 py-2.5 px-4 text-sm font-semibold rounded-xl transition-all ${
                    gender === 'male'
                      ? 'bg-white text-slate-800 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.1)]'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'
                  }`}
                >
                  General
                </button>
                <button
                  type="button"
                  onClick={() => setGender('female')}
                  className={`flex-1 py-2.5 px-4 text-sm font-semibold rounded-xl transition-all ${
                    gender === 'female'
                      ? 'bg-white text-rose-700 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.1)]'
                      : 'text-slate-500 hover:text-slate-700 hover:bg-slate-200/50'
                  }`}
                >
                  Female <span className="opacity-70 font-normal">(₹0 MTC)</span>
                </button>
              </div>
            </div>
          </div>

          {/* CTA Button - Active only when both locations have valid selections and coordinates */}
          <button
            type="submit"
            disabled={!isFormValid}
            className={`w-full rounded-2xl py-4 flex items-center justify-center gap-2 transition-all font-bold text-lg shadow-lg ${
              isFormValid
                ? 'bg-rose-700 hover:bg-rose-800 active:bg-rose-900 text-white shadow-rose-700/25 hover:shadow-xl hover:-translate-y-0.5 cursor-pointer group'
                : 'bg-slate-200 text-slate-400 shadow-none cursor-not-allowed opacity-90'
            }`}
          >
            <Search size={22} className={isFormValid ? 'group-hover:scale-110 transition-transform' : ''} />
            <span>Search Transit Routes</span>
          </button>
        </form>
      </div>

      {/* Footer / Popular Corridors */}
      <div className="mt-12 text-center w-full max-w-3xl">
        <div className="flex items-center justify-center gap-2 text-slate-400 mb-6">
          <div className="h-px bg-slate-200 w-12" />
          <span className="text-xs font-semibold uppercase tracking-widest">
            Popular Verified Corridors
          </span>
          <div className="h-px bg-slate-200 w-12" />
        </div>

        <div className="flex flex-wrap justify-center gap-3">
          {[
            { source: 'Central Dental College', destination: 'Guindy B.T' },
            { source: '12Th Main Road Anna Nagar', destination: 'Guindy B.T' },
            { source: 'Adyar Aavin', destination: 'Guindy Cipet' },
          ].map((route, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => selectPopularRoute(route.source, route.destination)}
              className="flex items-center gap-2 bg-white border border-slate-200 hover:border-slate-300 px-4 py-2.5 rounded-full text-sm font-medium text-slate-600 hover:text-slate-900 shadow-sm hover:shadow transition-all group"
            >
              <Navigation size={14} className="text-slate-400 group-hover:text-rose-500" />
              <span>
                {route.source} → {route.destination}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
