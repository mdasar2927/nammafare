'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  MapPin,
  Navigation,
  X,
  Map,
  Loader2,
  CheckCircle2,
} from 'lucide-react';
import { GPSButton } from '@/components/GPSButton';
import { LocationSuggestions } from '@/components/LocationSuggestions';
import { searchUnifiedLocations, LocationSuggestionItem } from '@/lib/api';

// Dynamic import MapPickerModal to prevent SSR issues with Leaflet
const MapPickerModal = dynamic(
  () => import('@/components/MapPickerModal').then((m) => m.MapPickerModal),
  { ssr: false }
);

interface LocationInputProps {
  id: string;
  label: string;
  placeholder?: string;
  value: string;
  coords: { lat: number; lng: number } | null;
  sourceType?: 'Theme7' | 'OpenStreetMap' | 'GPS' | 'Map' | string;
  iconType?: 'origin' | 'destination';
  onChange: (value: string, coords: { lat: number; lng: number } | null, sourceType?: string) => void;
  required?: boolean;
}

export function LocationInput({
  id,
  label,
  placeholder = 'Search stops, stations, addresses or landmarks',
  value,
  coords,
  sourceType,
  iconType = 'origin',
  onChange,
  required = true,
}: LocationInputProps) {
  const [inputValue, setInputValue] = useState(value);
  const [isOpen, setIsOpen] = useState(false);
  const [isMapModalOpen, setIsMapModalOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const [suggestions, setSuggestions] = useState<{
    transit: LocationSuggestionItem[];
    places: LocationSuggestionItem[];
  }>({ transit: [], places: [] });

  const containerRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Sync external value changes (e.g. after swap)
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  // Handle outside click to close suggestions
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Debounced search query
  const performSearch = useCallback(async (query: string) => {
    setIsLoading(true);
    try {
      const results = await searchUnifiedLocations(query);
      setSuggestions(results);
      setIsOpen(true);
    } catch (err) {
      console.warn('Location search failed:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);
    // When user types custom text, clear attached coordinates until picked or resolved
    onChange(val, null, undefined);

    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      performSearch(val);
    }, 250);
  };

  const handleFocus = () => {
    performSearch(inputValue);
  };

  const handleClear = () => {
    setInputValue('');
    onChange('', null, undefined);
    setSuggestions({ transit: [], places: [] });
    setIsOpen(false);
  };

  const handleSelectSuggestion = (item: LocationSuggestionItem) => {
    setInputValue(item.name);
    onChange(item.name, { lat: item.lat, lng: item.lng }, item.source);
    setIsOpen(false);
  };

  const handleGPSLocation = (detected: {
    name: string;
    lat: number;
    lng: number;
    source: 'GPS';
  }) => {
    setInputValue(detected.name);
    onChange(detected.name, { lat: detected.lat, lng: detected.lng }, 'GPS');
    setIsOpen(false);
  };

  const handleMapConfirm = (picked: {
    name: string;
    lat: number;
    lng: number;
    source: 'Map';
  }) => {
    setInputValue(picked.name);
    onChange(picked.name, { lat: picked.lat, lng: picked.lng }, 'Map');
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className="relative w-full">
      {/* Label Row with Quick Action Buttons */}
      <div className="flex items-center justify-between mb-1.5">
        <label
          htmlFor={id}
          className="text-xs font-semibold text-slate-700 uppercase tracking-wider"
        >
          {label}
        </label>

        {/* Header Action Shortcuts: GPS + Choose on Map */}
        <div className="flex items-center gap-1.5">
          <GPSButton onLocationDetected={handleGPSLocation} variant="badge" />

          <button
            type="button"
            onClick={() => setIsMapModalOpen(true)}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold text-brand-900 bg-rose-50/80 hover:bg-rose-100 rounded-xl border border-rose-200/80 transition-all shadow-sm"
            title="Pick exact location on interactive map"
          >
            <Map size={12} className="text-brand-700" />
            <span className="hidden sm:inline">Choose on</span> Map
          </button>
        </div>
      </div>

      {/* Input Field Container */}
      <div className="relative flex items-center">
        {/* Leading Mode Icon */}
        <div className="absolute left-3.5 text-slate-400 pointer-events-none">
          {iconType === 'origin' ? (
            <Navigation size={18} className="text-rose-600 transform rotate-45" />
          ) : (
            <MapPin size={18} className="text-brand-800" />
          )}
        </div>

        {/* Text Input */}
        <input
          id={id}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onFocus={handleFocus}
          placeholder={placeholder}
          required={required}
          autoComplete="off"
          className="w-full pl-11 pr-20 py-3.5 bg-slate-50/70 hover:bg-slate-50 focus:bg-white text-slate-900 text-sm font-medium rounded-2xl border border-slate-200/90 focus:border-brand-600 focus:ring-4 focus:ring-brand-500/10 transition-all outline-none"
        />

        {/* Trailing Action Icons (Clear, Loading, GPS) */}
        <div className="absolute right-2.5 flex items-center gap-1">
          {isLoading && (
            <Loader2 size={16} className="animate-spin text-slate-400 mr-1" />
          )}

          {inputValue && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
              title="Clear text"
            >
              <X size={14} />
            </button>
          )}

          <GPSButton onLocationDetected={handleGPSLocation} variant="icon" />
        </div>
      </div>

      {/* Coordinate & Source Provenance Tag */}
      {coords && (
        <div className="mt-1.5 flex items-center gap-2 text-[10px] text-slate-500">
          <span className="inline-flex items-center gap-1 font-mono text-emerald-800 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
            <CheckCircle2 size={11} className="text-emerald-600" />
            {coords.lat.toFixed(4)}°, {coords.lng.toFixed(4)}°
          </span>
          {sourceType && (
            <span className="font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
              {sourceType}
            </span>
          )}
        </div>
      )}

      {/* Autocomplete Suggestions Dropdown */}
      {isOpen && (
        <LocationSuggestions
          suggestions={suggestions}
          onSelect={handleSelectSuggestion}
          onClose={() => setIsOpen(false)}
        />
      )}

      {/* Interactive Map Picker Modal */}
      {isMapModalOpen && (
        <MapPickerModal
          isOpen={isMapModalOpen}
          onClose={() => setIsMapModalOpen(false)}
          title={`Choose ${label} on Map`}
          initialLat={coords?.lat || 13.0827}
          initialLng={coords?.lng || 80.2707}
          initialName={inputValue}
          onConfirm={handleMapConfirm}
        />
      )}
    </div>
  );
}
