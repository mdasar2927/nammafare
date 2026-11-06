'use client';

import React, { useState, useRef, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  CircleDot,
  MapPin,
  X,
  Map as MapIcon,
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
  placeholder?: string;
  value: string;
  coords: { lat: number; lng: number } | null;
  sourceType?: string;
  iconType?: 'origin' | 'destination';
  onChange: (value: string, coords: { lat: number; lng: number } | null, sourceType?: string) => void;
  required?: boolean;
}

export function LocationInput({
  id,
  placeholder = 'Starting Point (Origin)',
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

  // Sync external value changes (e.g. after swap or clear)
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
    const trimmed = query.trim();
    if (!trimmed) {
      setSuggestions({ transit: [], places: [] });
      setIsOpen(false);
      return;
    }

    setIsLoading(true);
    try {
      const results = await searchUnifiedLocations(trimmed);
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
    if (!val.trim()) {
      setSuggestions({ transit: [], places: [] });
      setIsOpen(false);
      return;
    }

    debounceTimerRef.current = setTimeout(() => {
      performSearch(val);
    }, 250);
  };

  const handleFocus = () => {
    if (inputValue.trim().length >= 1) {
      performSearch(inputValue);
    }
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
    <div ref={containerRef} className={`relative w-full ${isOpen ? 'z-30' : 'z-10'}`}>
      <div className="relative flex flex-col bg-slate-50/50 rounded-2xl border border-slate-200 transition-all focus-within:border-rose-400 focus-within:bg-white focus-within:ring-4 focus-within:ring-rose-50 hover:border-slate-300">
        <div className="flex items-center">
          <div className={`pl-4 pr-3 ${iconType === 'origin' ? 'text-slate-400' : 'text-rose-600'}`}>
            {iconType === 'origin' ? (
              <CircleDot size={20} strokeWidth={2.5} />
            ) : (
              <MapPin size={20} strokeWidth={2.5} />
            )}
          </div>
          <input
            id={id}
            type="text"
            value={inputValue}
            onChange={handleInputChange}
            onFocus={handleFocus}
            placeholder={placeholder}
            required={required}
            autoComplete="off"
            className="w-full bg-transparent py-4 text-slate-800 font-medium placeholder:text-slate-400 focus:outline-none text-base sm:text-lg"
          />
          <div className="flex items-center gap-1 pr-2">
            {isLoading && (
              <Loader2 size={16} className="animate-spin text-slate-400 mr-1" />
            )}
            {inputValue && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1.5 text-slate-400 hover:text-slate-600 rounded-lg transition-colors"
                title="Clear text"
              >
                <X size={16} />
              </button>
            )}
            <GPSButton onLocationDetected={handleGPSLocation} variant="icon" />
            <button
              type="button"
              onClick={() => setIsMapModalOpen(true)}
              className="p-2 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-xl transition-all"
              title="Choose on Map"
            >
              <MapIcon size={20} />
            </button>
          </div>
        </div>

        {coords && (
          <div className="px-4 pb-2.5 -mt-1 flex items-center gap-2 text-[10px] text-slate-500">
            <span className="inline-flex items-center gap-1 font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
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
      </div>

      {isOpen && (
        <LocationSuggestions
          suggestions={suggestions}
          onSelect={handleSelectSuggestion}
          onClose={() => setIsOpen(false)}
        />
      )}

      {isMapModalOpen && (
        <MapPickerModal
          isOpen={isMapModalOpen}
          onClose={() => setIsMapModalOpen(false)}
          title={placeholder || 'Choose on Map'}
          initialLat={coords?.lat || 13.0827}
          initialLng={coords?.lng || 80.2707}
          initialName={inputValue}
          onConfirm={handleMapConfirm}
        />
      )}
    </div>
  );
}
