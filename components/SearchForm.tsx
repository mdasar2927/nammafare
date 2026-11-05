'use client';

import React, { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  MapPin,
  ArrowUpDown,
  Search,
  Sparkles,
  Navigation,
  Compass,
  Loader2,
} from 'lucide-react';
import { POPULAR_ROUTES } from '@/data/locations';
import { Gender, SortPreference, ChennaiLocation } from '@/types/transit';
import { fetchPlaces } from '@/lib/api';
import { GenderToggle } from '@/components/GenderToggle';
import { SortToggle } from '@/components/SortToggle';

export function SearchForm() {
  const router = useRouter();

  const [source, setSource] = useState('Central Dental College');
  const [sourceCoords, setSourceCoords] = useState<{ lat: number; lng: number } | null>({
    lat: 13.0828,
    lng: 80.2822,
  });

  const [destination, setDestination] = useState('Guindy B.T');
  const [destCoords, setDestCoords] = useState<{ lat: number; lng: number } | null>({
    lat: 13.0092,
    lng: 80.2108,
  });

  const [gender, setGender] = useState<Gender>('male');
  const [sortBy, setSortBy] = useState<SortPreference>('cost');

  const [sourceSuggestions, setSourceSuggestions] = useState<ChennaiLocation[]>([]);
  const [destSuggestions, setDestSuggestions] = useState<ChennaiLocation[]>([]);
  const [activeInput, setActiveInput] = useState<'source' | 'destination' | null>(null);
  const [isLoadingSuggestions, setIsLoadingSuggestions] = useState(false);

  const formRef = useRef<HTMLDivElement>(null);

  // Close suggestions when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (formRef.current && !formRef.current.contains(event.target as Node)) {
        setActiveInput(null);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fetch suggestions from backend places API
  const handleSourceChange = async (val: string) => {
    setSource(val);
    setSourceCoords(null);
    setIsLoadingSuggestions(true);
    try {
      const places = await fetchPlaces(val, 8);
      setSourceSuggestions(places);
    } catch {
      // handled in fetchPlaces fallback
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  const handleDestChange = async (val: string) => {
    setDestination(val);
    setDestCoords(null);
    setIsLoadingSuggestions(true);
    try {
      const places = await fetchPlaces(val, 8);
      setDestSuggestions(places);
    } catch {
      // handled in fetchPlaces fallback
    } finally {
      setIsLoadingSuggestions(false);
    }
  };

  const swapLocations = () => {
    const tempSrc = source;
    const tempCoords = sourceCoords;
    setSource(destination);
    setSourceCoords(destCoords);
    setDestination(tempSrc);
    setDestCoords(tempCoords);
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
    try {
      const p1 = await fetchPlaces(src, 1);
      if (p1.length > 0 && typeof p1[0].lat === 'number' && typeof p1[0].lng === 'number') {
        setSourceCoords({ lat: p1[0].lat, lng: p1[0].lng });
      }
      const p2 = await fetchPlaces(dst, 1);
      if (p2.length > 0 && typeof p2[0].lat === 'number' && typeof p2[0].lng === 'number') {
        setDestCoords({ lat: p2[0].lat, lng: p2[0].lng });
      }
    } catch {
      // ignore
    }
  };

  return (
    <div ref={formRef} className="w-full">
      <form
        onSubmit={handleSubmit}
        className="bg-white rounded-3xl p-6 sm:p-8 shadow-soft-xl border border-rose-100/90 relative"
      >
        {/* Glow Header Accent */}
        <div className="absolute top-0 inset-x-8 h-1 bg-gradient-to-r from-brand-700 via-rose-500 to-brand-900 rounded-t-full" />

        <div className="flex flex-col gap-6">
          {/* Inputs Section */}
          <div className="grid grid-cols-1 lg:grid-cols-[1fr,auto,1fr] items-center gap-3 relative">
            {/* Source Input */}
            <div className="relative">
              <label
                htmlFor="source-input"
                className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5"
              >
                Starting Point (Origin)
              </label>
              <div className="relative flex items-center">
                <div className="absolute left-3.5 text-rose-600 pointer-events-none">
                  <Navigation size={18} className="transform rotate-45" />
                </div>
                <input
                  id="source-input"
                  type="text"
                  value={source}
                  onChange={(e) => handleSourceChange(e.target.value)}
                  onFocus={async () => {
                    setActiveInput('source');
                    const places = await fetchPlaces(source || '', 8);
                    setSourceSuggestions(places);
                  }}
                  placeholder="Search Theme7 stops, stations, or areas"
                  required
                  className="w-full pl-11 pr-4 py-3.5 bg-slate-50/70 hover:bg-slate-50 focus:bg-white text-slate-900 text-sm font-medium rounded-2xl border border-slate-200/90 focus:border-brand-600 focus:ring-4 focus:ring-brand-500/10 transition-all outline-none"
                />
                {isLoadingSuggestions && activeInput === 'source' && (
                  <div className="absolute right-3 text-slate-400">
                    <Loader2 size={16} className="animate-spin" />
                  </div>
                )}
              </div>

              {/* Source Autocomplete Dropdown */}
              {activeInput === 'source' && sourceSuggestions.length > 0 && (
                <div className="absolute left-0 right-0 top-full mt-2 bg-white rounded-2xl shadow-soft-xl border border-rose-100/90 z-30 max-h-64 overflow-y-auto p-2">
                  <div className="text-[11px] font-bold text-slate-400 px-3 py-1.5 uppercase tracking-wider flex items-center justify-between">
                    <span>Theme7 Places & Transit Stops</span>
                    <span className="text-[10px] text-emerald-600 font-normal">Official GIS</span>
                  </div>
                  {sourceSuggestions.map((loc) => (
                    <button
                      key={loc.id}
                      type="button"
                      onClick={() => {
                        setSource(loc.name);
                        if (loc.lat && loc.lng) {
                          setSourceCoords({ lat: loc.lat, lng: loc.lng });
                        }
                        setActiveInput(null);
                      }}
                      className="w-full text-left px-3 py-2 rounded-xl hover:bg-rose-50/80 transition-colors flex items-center justify-between group"
                    >
                      <div className="flex items-center gap-2.5 truncate mr-2">
                        <MapPin size={15} className="text-brand-600 shrink-0 group-hover:scale-110 transition-transform" />
                        <div className="truncate">
                          <div className="text-xs font-semibold text-slate-800 truncate">{loc.name}</div>
                          {loc.description && (
                            <div className="text-[11px] text-slate-400 truncate">{loc.description}</div>
                          )}
                        </div>
                      </div>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 shrink-0 group-hover:bg-rose-100 group-hover:text-brand-800">
                        {loc.hubType || loc.category || 'Transit'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Swap Button */}
            <div className="flex justify-center -my-1 lg:my-0 lg:pt-6">
              <button
                type="button"
                onClick={swapLocations}
                title="Swap origin and destination"
                className="w-10 h-10 rounded-full bg-rose-50 hover:bg-rose-100 border border-rose-200 text-brand-900 flex items-center justify-center transition-all hover:rotate-180 duration-300 shadow-sm"
              >
                <ArrowUpDown size={16} />
              </button>
            </div>

            {/* Destination Input */}
            <div className="relative">
              <label
                htmlFor="dest-input"
                className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5"
              >
                Destination (Arrival)
              </label>
              <div className="relative flex items-center">
                <div className="absolute left-3.5 text-brand-800 pointer-events-none">
                  <MapPin size={18} />
                </div>
                <input
                  id="dest-input"
                  type="text"
                  value={destination}
                  onChange={(e) => handleDestChange(e.target.value)}
                  onFocus={async () => {
                    setActiveInput('destination');
                    const places = await fetchPlaces(destination || '', 8);
                    setDestSuggestions(places);
                  }}
                  placeholder="Search Theme7 stops, stations, or areas"
                  required
                  className="w-full pl-11 pr-4 py-3.5 bg-slate-50/70 hover:bg-slate-50 focus:bg-white text-slate-900 text-sm font-medium rounded-2xl border border-slate-200/90 focus:border-brand-600 focus:ring-4 focus:ring-brand-500/10 transition-all outline-none"
                />
                {isLoadingSuggestions && activeInput === 'destination' && (
                  <div className="absolute right-3 text-slate-400">
                    <Loader2 size={16} className="animate-spin" />
                  </div>
                )}
              </div>

              {/* Destination Autocomplete Dropdown */}
              {activeInput === 'destination' && destSuggestions.length > 0 && (
                <div className="absolute left-0 right-0 top-full mt-2 bg-white rounded-2xl shadow-soft-xl border border-rose-100/90 z-30 max-h-64 overflow-y-auto p-2">
                  <div className="text-[11px] font-bold text-slate-400 px-3 py-1.5 uppercase tracking-wider flex items-center justify-between">
                    <span>Theme7 Places & Transit Stops</span>
                    <span className="text-[10px] text-emerald-600 font-normal">Official GIS</span>
                  </div>
                  {destSuggestions.map((loc) => (
                    <button
                      key={loc.id}
                      type="button"
                      onClick={() => {
                        setDestination(loc.name);
                        if (loc.lat && loc.lng) {
                          setDestCoords({ lat: loc.lat, lng: loc.lng });
                        }
                        setActiveInput(null);
                      }}
                      className="w-full text-left px-3 py-2 rounded-xl hover:bg-rose-50/80 transition-colors flex items-center justify-between group"
                    >
                      <div className="flex items-center gap-2.5 truncate mr-2">
                        <MapPin size={15} className="text-brand-600 shrink-0 group-hover:scale-110 transition-transform" />
                        <div className="truncate">
                          <div className="text-xs font-semibold text-slate-800 truncate">{loc.name}</div>
                          {loc.description && (
                            <div className="text-[11px] text-slate-400 truncate">{loc.description}</div>
                          )}
                        </div>
                      </div>
                      <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 shrink-0 group-hover:bg-rose-100 group-hover:text-brand-800">
                        {loc.hubType || loc.category || 'Transit'}
                      </span>
                    </button>
                  ))}
                </div>
              )}
            </div>
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
