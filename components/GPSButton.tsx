'use client';

import React, { useState } from 'react';
import { Crosshair, Loader2, AlertCircle } from 'lucide-react';
import { reverseGeocodeCoords } from '@/lib/api';

interface GPSButtonProps {
  onLocationDetected: (location: {
    name: string;
    lat: number;
    lng: number;
    source: 'GPS';
  }) => void;
  className?: string;
  variant?: 'icon' | 'badge';
}

export function GPSButton({
  onLocationDetected,
  className = '',
  variant = 'icon',
}: GPSButtonProps) {
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleGetLocation = () => {
    if (typeof window === 'undefined' || !navigator.geolocation) {
      setErrorMessage('Geolocation is not supported by your browser');
      setTimeout(() => setErrorMessage(null), 4000);
      return;
    }

    setIsLoading(true);
    setErrorMessage(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const { latitude, longitude } = pos.coords;

        try {
          // Attempt reverse geocoding
          const geo = await reverseGeocodeCoords(latitude, longitude);
          onLocationDetected({
            name: geo.name || `Current Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`,
            lat: latitude,
            lng: longitude,
            source: 'GPS',
          });
        } catch {
          // Fallback to raw coordinates
          onLocationDetected({
            name: `Current Location (${latitude.toFixed(4)}, ${longitude.toFixed(4)})`,
            lat: latitude,
            lng: longitude,
            source: 'GPS',
          });
        } finally {
          setIsLoading(false);
        }
      },
      (err) => {
        setIsLoading(false);
        let msg = 'Could not detect your location.';
        if (err.code === err.PERMISSION_DENIED) {
          msg = 'Location permission denied. Please allow location access in your browser.';
        } else if (err.code === err.POSITION_UNAVAILABLE) {
          msg = 'GPS signal unavailable. Please select on the map or type an address.';
        } else if (err.code === err.TIMEOUT) {
          msg = 'Location detection timed out. Please try again.';
        }
        setErrorMessage(msg);
        setTimeout(() => setErrorMessage(null), 5000);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 30000,
      }
    );
  };

  return (
    <div className="relative inline-flex items-center">
      {variant === 'badge' ? (
        <button
          type="button"
          onClick={handleGetLocation}
          disabled={isLoading}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-rose-700 bg-rose-50 hover:bg-rose-100/90 active:bg-rose-200 rounded-xl border border-rose-200/80 transition-all shadow-sm ${className}`}
          title="Use your device's live GPS coordinates"
        >
          {isLoading ? (
            <Loader2 size={13} className="animate-spin text-rose-600" />
          ) : (
            <Crosshair size={13} className="text-rose-600" />
          )}
          <span>{isLoading ? 'Detecting GPS...' : 'Use Current Location'}</span>
        </button>
      ) : (
        <button
          type="button"
          onClick={handleGetLocation}
          disabled={isLoading}
          className={`p-2 rounded-xl text-slate-500 hover:text-brand-900 hover:bg-rose-50/80 transition-colors ${className}`}
          title="Use my current GPS location"
        >
          {isLoading ? (
            <Loader2 size={16} className="animate-spin text-rose-600" />
          ) : (
            <Crosshair size={16} className="text-slate-600 hover:text-brand-800" />
          )}
        </button>
      )}

      {/* Temporary Toast Error Message */}
      {errorMessage && (
        <div className="absolute top-full mt-2 right-0 z-50 w-64 p-2.5 rounded-xl bg-rose-900 text-white text-[11px] shadow-soft-lg flex items-start gap-2 animate-in fade-in slide-in-from-top-1">
          <AlertCircle size={14} className="text-rose-300 shrink-0 mt-0.5" />
          <span className="leading-snug">{errorMessage}</span>
        </div>
      )}
    </div>
  );
}
