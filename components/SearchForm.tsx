'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowUpDown, Search, Sparkles, Compass } from 'lucide-react';
import { POPULAR_ROUTES } from '@/data/locations';
import { Gender, SortPreference } from '@/types/transit';
import { resolveCoordinates } from '@/lib/api';
import { LocationInput } from '@/components/LocationInput';
import { GenderToggle } from '@/components/GenderToggle';
import { SortToggle } from '@/components/SortToggle';

export function SearchForm() {
  const router = useRouter();

  const [source, setSource] = useState('Central Dental College');
  const [sourceCoords, setSourceCoords] = useState<{ lat: number; lng: number } | null>({
    lat: 13.0828,
    lng: 80.2822,
  });
  const [sourceType, setSourceType] = useState<string | undefined>('Theme7 Stop');

  const [destination, setDestination] = useState('Guindy B.T');
  const [destCoords, setDestCoords] = useState<{ lat: number; lng: number } | null>({
    lat: 13.0092,
    lng: 80.2108,
  });
  const [destType, setDestType] = useState<string | undefined>('Theme7 Stop');

  const [gender, setGender] = useState<Gender>('male');
  const [sortBy, setSortBy] = useState<SortPreference>('cost');

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
    if (!source.trim() || !destination.trim()) return;

    const params = new URLSearchParams({
      source: source.trim(),
      destination: destination.trim(),
      gender,
      sort: sortBy,
    });

    if (sourceCoords) {
      params.set('sLat', sourceCoords.lat.toString());
      params.set('sLng', sourceCoords.lng.toString());
    }
    if (destCoords) {
      params.set('dLat', destCoords.lat.toString());
      params.set('dLng', destCoords.lng.toString());
    }

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
    <div className="w-full">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-3xl p-6 sm:p-8 shadow-soft-xl border border-rose-100/90 relative"
      >
        {/* Glow Header Accent */}
        <div className="absolute top-0 inset-x-8 h-1 bg-gradient-to-r from-brand-700 via-rose-500 to-brand-900 rounded-t-full" />

        <div className="flex flex-col gap-6">
          {/* Inputs Section: Origin, Swap Button, Destination */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr,auto,1fr] items-start gap-4 relative">
            {/* Origin Location Input */}
            <LocationInput
              id="source-input"
              label="Starting Point (Origin)"
              placeholder="Search stop, address, landmark, or pick on map"
              value={source}
              coords={sourceCoords}
              sourceType={sourceType}
              iconType="origin"
              onChange={handleSourceChange}
            />

            {/* Swap Button */}
            <div className="flex justify-center my-0 lg:pt-8">
              <button
                type="button"
                onClick={swapLocations}
                title="Swap origin and destination"
                className="w-10 h-10 rounded-full bg-rose-50 hover:bg-rose-100 border border-rose-200 text-brand-800 flex items-center justify-center transition-all hover:rotate-180 duration-300 shadow-sm"
              >
                <ArrowUpDown size={16} />
              </button>
            </div>

            {/* Destination Location Input */}
            <LocationInput
              id="dest-input"
              label="Destination (Arrival)"
              placeholder="Search stop, address, landmark, or pick on map"
              value={destination}
              coords={destCoords}
              sourceType={destType}
              iconType="destination"
              onChange={handleDestChange}
            />
          </div>

          {/* Preferences Section: Sort By + Gender Toggle */}
          <div className="pt-2 border-t border-slate-100 grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
            <SortToggle sortBy={sortBy} onChange={setSortBy} />
            <GenderToggle gender={gender} onChange={setGender} />
          </div>

          {/* Prominent Action Button */}
          <div className="pt-2">
            <button
              type="submit"
              className="w-full py-4 px-6 rounded-2xl bg-gradient-to-r from-brand-900 via-brand-800 to-rose-700 hover:from-brand-950 hover:to-brand-800 text-white font-bold text-base shadow-soft-lg hover:shadow-soft-xl transition-all duration-200 flex items-center justify-center gap-2.5 group"
            >
              <Search size={20} className="group-hover:scale-110 transition-transform" />
              <span>Search Transit Routes</span>
              <Compass size={18} className="text-rose-300 opacity-80" />
            </button>
          </div>
        </div>
      </form>

      {/* Popular Chennai Commutes Quick Chips */}
      <div className="mt-6 flex flex-wrap items-center gap-2 justify-center">
        <span className="text-xs font-medium text-slate-500 flex items-center gap-1">
          <Sparkles size={12} className="text-brand-600" />
          Verified Corridors:
        </span>
        {POPULAR_ROUTES.map((route, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => selectPopularRoute(route.source, route.destination)}
            className="text-xs font-medium bg-white/80 hover:bg-rose-50 border border-rose-100/80 hover:border-brand-200 text-slate-700 hover:text-brand-900 px-3 py-1.5 rounded-full transition-all shadow-sm"
          >
            {route.source} ➔ {route.destination}
          </button>
        ))}
      </div>
    </div>
  );
}
