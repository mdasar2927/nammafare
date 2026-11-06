'use client';

import React, { useMemo, useEffect } from 'react';
import { MapContainer, TileLayer, Marker, useMapEvents, useMap } from 'react-leaflet';
import L from 'leaflet';

interface MapPickerLeafletProps {
  initialLat: number;
  initialLng: number;
  currentLat: number;
  currentLng: number;
  label: string;
  onPositionChange: (lat: number, lng: number) => void;
}

const createPinIcon = (label: string) => {
  return L.divIcon({
    className: 'custom-leaflet-marker',
    html: `
      <div style="position: relative; display: flex; flex-direction: column; align-items: center; transform: translate(-50%, -100%); pointer-events: none;">
        <div style="background: #881337; color: white; padding: 3px 8px; border-radius: 9999px; font-weight: bold; font-size: 11px; white-space: nowrap; box-shadow: 0 4px 10px rgba(0,0,0,0.25); border: 2px solid white; margin-bottom: 2px;">
          ${label}
        </div>
        <div style="width: 26px; height: 26px; background: #881337; border-radius: 50% 50% 50% 0; transform: rotate(-45deg); border: 2.5px solid white; box-shadow: 0 4px 12px rgba(136,19,55,0.45); display: flex; align-items: center; justify-content: center;">
          <div style="width: 7px; height: 7px; background: white; border-radius: 50%;"></div>
        </div>
      </div>
    `,
    iconSize: [30, 42],
    iconAnchor: [15, 42],
  });
};

function LocationMarker({
  position,
  onPositionChange,
  label,
}: {
  position: { lat: number; lng: number };
  onPositionChange: (lat: number, lng: number) => void;
  label: string;
}) {
  useMapEvents({
    click(e) {
      onPositionChange(e.latlng.lat, e.latlng.lng);
    },
  });

  const eventHandlers = useMemo(
    () => ({
      dragend(e: any) {
        const marker = e.target;
        if (marker) {
          const latLng = marker.getLatLng();
          onPositionChange(latLng.lat, latLng.lng);
        }
      },
    }),
    [onPositionChange]
  );

  return (
    <Marker
      draggable={true}
      eventHandlers={eventHandlers}
      position={[position.lat, position.lng]}
      icon={createPinIcon(label)}
    />
  );
}

function MapController({ lat, lng }: { lat: number; lng: number }) {
  const map = useMap();
  useEffect(() => {
    // Only pan if distance is significant to avoid jitter
    const currentCenter = map.getCenter();
    const dist = Math.hypot(currentCenter.lat - lat, currentCenter.lng - lng);
    if (dist > 0.005) {
      map.flyTo([lat, lng], map.getZoom(), { duration: 0.8 });
    }
  }, [lat, lng, map]);
  return null;
}

export default function MapPickerLeaflet({
  currentLat,
  currentLng,
  label,
  onPositionChange,
}: MapPickerLeafletProps) {
  return (
    <div className="w-full h-full relative">
      <MapContainer
        center={[currentLat, currentLng]}
        zoom={13}
        scrollWheelZoom={true}
        className="w-full h-full rounded-2xl"
        style={{ minHeight: '380px', height: '100%' }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <LocationMarker
          position={{ lat: currentLat, lng: currentLng }}
          onPositionChange={onPositionChange}
          label={label}
        />
        <MapController lat={currentLat} lng={currentLng} />
      </MapContainer>
    </div>
  );
}

