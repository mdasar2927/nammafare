'use client';

import React, { useState, useEffect, useCallback } from 'react';
import dynamic from 'next/dynamic';
import {
  X,
  MapPin,
  Check,
  Loader2,
  Navigation,
  Compass,
  Info,
} from 'lucide-react';
import { reverseGeocodeCoords } from '@/lib/api';

// Dynamic import with ssr: false to prevent Leaflet SSR issues
const MapPickerLeaflet = dynamic(() => import('@/components/MapPickerLeaflet'), {
  ssr: false,
  loading: () => (
    <div className="w-full h-[420px] bg-slate-100 rounded-2xl flex flex-col items-center justify-center gap-3 text-slate-500 animate-pulse">
      <Loader2 size={32} className="animate-spin text-brand-800" />
      <span className="text-xs font-semibold">Loading Chennai OpenStreetMap...</span>
    </div>
  ),
});

interface MapPickerModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  initialLat?: number;
  initialLng?: number;
  initialName?: string;
  onConfirm: (location: { name: string; lat: number; lng: number; source: 'Map' }) => void;
}

// Default Chennai Center (Puratchi Thalaivar Dr. M.G.R. Central)
const DEFAULT_CHENNAI_LAT = 13.0827;
const DEFAULT_CHENNAI_LNG = 80.2707;

export function MapPickerModal({
  isOpen,
  onClose,
  title,
  initialLat = DEFAULT_CHENNAI_LAT,
  initialLng = DEFAULT_CHENNAI_LNG,
  initialName,
  onConfirm,
}: MapPickerModalProps) {
  const [lat, setLat] = useState(initialLat || DEFAULT_CHENNAI_LAT);
  const [lng, setLng] = useState(initialLng || DEFAULT_CHENNAI_LNG);
  const [locationName, setLocationName] = useState(initialName || '');
  const [isReverseGeocoding, setIsReverseGeocoding] = useState(false);

  // Sync initial state when modal opens
  useEffect(() => {
    if (isOpen) {
      const activeLat = initialLat || DEFAULT_CHENNAI_LAT;
      const activeLng = initialLng || DEFAULT_CHENNAI_LNG;
      setLat(activeLat);
      setLng(activeLng);

      if (!initialName) {
        reverseGeocode(activeLat, activeLng);
      } else {
        setLocationName(initialName);
      }
    }
  }, [isOpen, initialLat, initialLng, initialName]);

  const reverseGeocode = useCallback(async (targetLat: number, targetLng: number) => {
    setIsReverseGeocoding(true);
    try {
      const res = await reverseGeocodeCoords(targetLat, targetLng);
      setLocationName(res.name);
    } catch {
      setLocationName(`Point (${targetLat.toFixed(4)}, ${targetLng.toFixed(4)})`);
    } finally {
      setIsReverseGeocoding(false);
    }
  }, []);

  const handlePositionChange = useCallback(
    (newLat: number, newLng: number) => {
      setLat(newLat);
      setLng(newLng);
      reverseGeocode(newLat, newLng);
    },
    [reverseGeocode]
  );

  const handleConfirm = () => {
    onConfirm({
      name: locationName || `Selected Point (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
      lat,
      lng,
      source: 'Map',
    });
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white w-full max-w-4xl rounded-3xl shadow-2xl border border-rose-100 flex flex-col max-h-[92vh] overflow-hidden">
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-rose-50/50 via-white to-transparent">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-brand-800 text-white flex items-center justify-center shadow-sm">
              <MapPin size={17} />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">{title}</h3>
              <p className="text-[11px] text-slate-500">
                Click anywhere in Chennai or drag the marker to choose exact coordinates
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-600 flex items-center justify-center transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Map Container Area */}
        <div className="relative flex-1 min-h-[380px] sm:min-h-[460px] p-4 bg-slate-50">
          <MapPickerLeaflet
            initialLat={DEFAULT_CHENNAI_LAT}
            initialLng={DEFAULT_CHENNAI_LNG}
            currentLat={lat}
            currentLng={lng}
            label={title.includes('Origin') ? 'Origin' : 'Destination'}
            onPositionChange={handlePositionChange}
          />

          {/* Quick instructions floating badge */}
          <div className="absolute top-6 left-6 z-20 bg-white/95 backdrop-blur-sm px-3 py-1.5 rounded-full border border-slate-200/90 shadow-soft-sm text-[11px] font-semibold text-slate-700 flex items-center gap-1.5">
            <Compass size={13} className="text-brand-800" />
            <span>Click map or drag pin to adjust</span>
          </div>
        </div>

        {/* Modal Footer / Selected Info & Actions */}
        <div className="px-6 py-4 border-t border-slate-100 bg-white flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
          {/* Selected Location Details */}
          <div className="flex-1 truncate">
            <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400 mb-0.5">
              Selected Point
            </div>
            <div className="flex items-center gap-2">
              {isReverseGeocoding ? (
                <div className="flex items-center gap-1.5 text-xs text-brand-800 font-medium">
                  <Loader2 size={13} className="animate-spin text-brand-800" />
                  <span>Reverse geocoding address...</span>
                </div>
              ) : (
                <div className="text-xs sm:text-sm font-bold text-slate-900 truncate">
                  {locationName || 'Pin placed on map'}
                </div>
              )}
            </div>

            <div className="text-[11px] font-mono text-slate-400 mt-0.5">
              Lat: {lat.toFixed(5)}° N • Lng: {lng.toFixed(5)}° E
            </div>
          </div>

          {/* Confirm & Cancel Buttons */}
          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold text-xs transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleConfirm}
              className="px-5 py-2.5 rounded-xl bg-brand-800 hover:bg-brand-900 active:bg-brand-950 text-white font-bold text-xs flex items-center gap-1.5 shadow-soft-md transition-all"
            >
              <Check size={15} />
              <span>Confirm Location</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

