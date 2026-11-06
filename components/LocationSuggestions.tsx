'use client';

import React from 'react';
import { LocationSuggestionItem } from '@/lib/api';
import {
  Bus,
  Train,
  TramFront,
  MapPin,
  Building2,
  Navigation,
  Compass,
  Database,
} from 'lucide-react';

interface LocationSuggestionsProps {
  suggestions: {
    transit: LocationSuggestionItem[];
    places: LocationSuggestionItem[];
  };
  onSelect: (item: LocationSuggestionItem) => void;
  onClose: () => void;
}

export function LocationSuggestions({
  suggestions,
  onSelect,
}: LocationSuggestionsProps) {
  const { transit, places } = suggestions;
  const hasTransit = transit.length > 0;
  const hasPlaces = places.length > 0;

  if (!hasTransit && !hasPlaces) {
    return (
      <div className="absolute left-0 right-0 top-full mt-2 bg-white rounded-2xl shadow-soft-xl border border-rose-100/90 z-40 p-4 text-center">
        <p className="text-xs text-slate-500">
          No matching Theme7 transit stops or Chennai landmarks found.
        </p>
      </div>
    );
  }

  const renderIcon = (cat: string, group: 'transit' | 'places') => {
    const c = cat.toLowerCase();
    if (c.includes('metro')) return <Train size={15} className="text-sky-600" />;
    if (c.includes('suburban') || c.includes('rail')) return <TramFront size={15} className="text-indigo-600" />;
    if (c.includes('bus')) return <Bus size={15} className="text-orange-600" />;
    if (group === 'transit') return <Navigation size={15} className="text-brand-700" />;
    if (c.includes('address') || c.includes('road')) return <MapPin size={15} className="text-rose-600" />;
    return <Building2 size={15} className="text-slate-600" />;
  };

  return (
    <div className="absolute left-0 right-0 top-full mt-2 bg-white rounded-2xl shadow-soft-xl border border-rose-100/90 z-40 max-h-80 overflow-y-auto divide-y divide-slate-100 p-2">
      {/* Group 1: Theme7 Public Transit Stops & Stations */}
      {hasTransit && (
        <div className="pb-2">
          <div className="px-3 py-1.5 flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            <span className="flex items-center gap-1.5 text-brand-900">
              <Bus size={13} className="text-brand-700" />
              Theme7 Public Transit Stops & Stations
            </span>
            <span className="text-[10px] text-emerald-700 font-mono bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
              Official Theme7
            </span>
          </div>

          <div className="space-y-0.5 mt-1">
            {transit.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect(item)}
                className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-rose-50/70 transition-colors flex items-center justify-between group"
              >
                <div className="flex items-center gap-3 truncate mr-2">
                  <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 group-hover:bg-rose-100 group-hover:text-brand-900 transition-colors">
                    {renderIcon(item.category, item.group)}
                  </div>
                  <div className="truncate">
                    <div className="text-xs font-semibold text-slate-800 truncate group-hover:text-brand-950">
                      {item.name}
                    </div>
                    {item.description && (
                      <div className="text-[11px] text-slate-400 truncate">
                        {item.description}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-600 group-hover:bg-rose-100 group-hover:text-brand-800">
                    {item.category}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Group 2: Landmarks, Localities & Addresses from OpenStreetMap */}
      {hasPlaces && (
        <div className={hasTransit ? 'pt-2' : ''}>
          <div className="px-3 py-1.5 flex items-center justify-between text-[11px] font-bold text-slate-400 uppercase tracking-wider">
            <span className="flex items-center gap-1.5 text-slate-700">
              <MapPin size={13} className="text-rose-600" />
              Chennai Landmarks & Addresses
            </span>
            <span className="text-[10px] text-slate-500 font-mono bg-slate-100 px-1.5 py-0.5 rounded">
              OpenStreetMap
            </span>
          </div>

          <div className="space-y-0.5 mt-1">
            {places.map((item) => (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelect(item)}
                className="w-full text-left px-3 py-2.5 rounded-xl hover:bg-slate-50 transition-colors flex items-center justify-between group"
              >
                <div className="flex items-center gap-3 truncate mr-2">
                  <div className="w-7 h-7 rounded-lg bg-rose-50/80 flex items-center justify-center shrink-0 text-brand-800">
                    {renderIcon(item.category, item.group)}
                  </div>
                  <div className="truncate">
                    <div className="text-xs font-semibold text-slate-800 truncate group-hover:text-brand-900">
                      {item.name}
                    </div>
                    {item.description && (
                      <div className="text-[11px] text-slate-400 truncate">
                        {item.description}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[10px] font-medium px-2 py-0.5 rounded-md bg-slate-100 text-slate-600">
                    {item.category}
                  </span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

