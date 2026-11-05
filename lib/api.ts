import {
  Gender,
  SortPreference,
  MultimodalRoute,
  RouteLeg,
  TransitMode,
  ChennaiLocation,
  BackendPlace,
  BackendSearchResponse,
} from '@/types/transit';
import { CHENNAI_LOCATIONS } from '@/data/locations';

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Check backend health status
 */
export async function fetchHealth(): Promise<{ status: string; version: string; data_loaded: boolean } | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/api/v1/health`, {
      cache: 'no-store',
    });
    if (!res.ok) return null;
    return await res.json();
  } catch (error) {
    console.warn('Backend healthcheck failed:', error);
    return null;
  }
}

/**
 * Fetch autocomplete suggestions for Chennai places and stops
 */
export async function fetchPlaces(query: string, limit = 8): Promise<ChennaiLocation[]> {
  try {
    const res = await fetch(
      `${API_BASE_URL}/api/v1/places?q=${encodeURIComponent(query)}&limit=${limit}`,
      { cache: 'no-store' }
    );
    if (!res.ok) throw new Error(`Places API responded with ${res.status}`);
    const places: BackendPlace[] = await res.json();

    if (places && places.length > 0) {
      return places.map((p) => {
        let hubType = 'Locality';
        if (p.category === 'interchange') hubType = 'Transit Hub';
        else if (p.category === 'metro_station') hubType = 'Metro';
        else if (p.category === 'railway_station') hubType = 'Railway';
        else if (p.category === 'bus_stop') hubType = 'Bus Stand';

        return {
          id: p.id,
          name: p.name,
          category: p.category,
          hubType,
          lat: p.lat,
          lng: p.lng,
          description: p.description,
        };
      });
    }
  } catch (err) {
    console.warn('Using local fallback for autocomplete places:', err);
  }

  // Fallback to local curated locations if backend is not responding or empty
  const qLower = query.toLowerCase().trim();
  if (!qLower) return CHENNAI_LOCATIONS.slice(0, limit);
  return CHENNAI_LOCATIONS.filter((l) =>
    l.name.toLowerCase().includes(qLower) || (l.tamilName && l.tamilName.includes(query))
  ).slice(0, limit);
}

/**
 * Resolve coordinates for a given place name
 */
export async function resolveCoordinates(
  placeName: string
): Promise<{ lat: number; lng: number }> {
  // Check known canonical spots
  const lower = placeName.toLowerCase();
  if (lower.includes('central')) return { lat: 13.0827, lng: 80.2755 };
  if (lower.includes('guindy')) return { lat: 13.0067, lng: 80.2128 };
  if (lower.includes('egmore')) return { lat: 13.0784, lng: 80.2612 };
  if (lower.includes('airport') || lower.includes('meenambakkam')) return { lat: 12.9806, lng: 80.1634 };
  if (lower.includes('tambaram')) return { lat: 12.9249, lng: 80.1197 };
  if (lower.includes('koyambedu') || lower.includes('cmbt')) return { lat: 13.0694, lng: 80.1948 };
  if (lower.includes('velachery')) return { lat: 12.9757, lng: 80.2207 };
  if (lower.includes('adyar')) return { lat: 13.0012, lng: 80.2565 };
  if (lower.includes('t. nagar') || lower.includes('nagar')) return { lat: 13.0418, lng: 80.2341 };

  // Query backend places endpoint
  try {
    const places = await fetchPlaces(placeName, 1);
    if (places && places.length > 0 && places[0].lat && places[0].lng) {
      return { lat: places[0].lat, lng: places[0].lng };
    }
  } catch {
    // ignore
  }

  // Fallback to central Chennai
  return { lat: 13.0827, lng: 80.2755 };
}

/**
 * Map backend mode string to frontend TransitMode
 */
function mapBackendMode(mode: string): TransitMode {
  const m = mode.toLowerCase().trim();
  if (m === 'bus') return 'mtc_bus';
  if (m === 'walking') return 'walking';
  if (m === 'metro') return 'metro';
  if (m === 'suburban_train') return 'suburban_train';
  if (m === 'auto') return 'auto';
  if (m === 'share_auto') return 'share_auto';
  if (m === 'taxi') return 'taxi';
  return 'walking';
}

export interface SearchRoutesParams {
  source: string;
  destination: string;
  sourceCoords?: { lat: number; lng: number };
  destCoords?: { lat: number; lng: number };
  gender: Gender;
  sortBy: SortPreference;
}

/**
 * Execute route search against the FastAPI backend
 */
export async function searchRoutesApi(
  params: SearchRoutesParams
): Promise<MultimodalRoute[]> {
  const { source, destination, gender, sortBy } = params;

  // Resolve coordinates
  const originCoords =
    params.sourceCoords && params.sourceCoords.lat && params.sourceCoords.lng
      ? params.sourceCoords
      : await resolveCoordinates(source);

  const destinationCoords =
    params.destCoords && params.destCoords.lat && params.destCoords.lng
      ? params.destCoords
      : await resolveCoordinates(destination);

  // Map frontend sort ('cost' | 'time') to backend sort ('cheapest' | 'fastest')
  const backendSortBy = sortBy === 'cost' ? 'cheapest' : 'fastest';

  const requestBody = {
    origin: {
      lat: originCoords.lat,
      lng: originCoords.lng,
      name: source,
    },
    destination: {
      lat: destinationCoords.lat,
      lng: destinationCoords.lng,
      name: destination,
    },
    gender: gender, // "male" or "female"
    allowed_modes: [
      'walking',
      'bus',
      'metro',
      'suburban_train',
      'auto',
      'share_auto',
      'taxi',
    ],
    sort_by: backendSortBy,
  };

  const res = await fetch(`${API_BASE_URL}/api/v1/routes/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(requestBody),
    cache: 'no-store',
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(`API Error (${res.status}): ${errorText}`);
  }

  const data: BackendSearchResponse = await res.json();

  if (!data.routes || data.routes.length === 0) {
    return [];
  }

  // Convert backend RouteOption[] to frontend MultimodalRoute[]
  return data.routes.map((r) => {
    const legs: RouteLeg[] = r.legs.map((leg, index) => {
      const mode = mapBackendMode(leg.mode);
      const isOrdinary = leg.bus_type === 'ordinary';
      const isVidiyalEligible = isOrdinary;

      let serviceType = leg.bus_type
        ? isOrdinary
          ? 'Ordinary White-Board Bus'
          : `MTC ${leg.bus_type.toUpperCase()}`
        : undefined;

      if (mode === 'suburban_train' && !serviceType) {
        serviceType = 'Southern Railway 2nd Class';
      } else if (mode === 'metro' && !serviceType) {
        serviceType = 'CMRL Metro';
      }

      return {
        id: `leg-${r.route_id}-${index}`,
        mode,
        fromStop: leg.from_name,
        toStop: leg.to_name,
        durationMinutes: leg.duration_minutes,
        distanceMeters: leg.distance_meters,
        fare: leg.fare,
        baseFareMale: leg.fare,
        fareType: leg.is_estimated ? 'estimated' : 'verified',
        routeNumber: leg.route_number || undefined,
        serviceType,
        isVidiyalEligible,
        fareNote: leg.fare_note || undefined,
        instructions: `${leg.from_name} to ${leg.to_name}`,
      };
    });

    const modes = Array.from(new Set(legs.map((l) => l.mode)));
    const hasVerifiedFaresOnly = !legs.some((l) => l.fareType === 'estimated');

    let highlightBadge: 'Cheapest' | 'Fastest' | 'Balanced' | undefined = undefined;
    if (r.is_cheapest) highlightBadge = 'Cheapest';
    else if (r.is_fastest) highlightBadge = 'Fastest';

    return {
      id: r.route_id,
      source: data.origin,
      destination: data.destination,
      summary: r.summary,
      totalDurationMinutes: r.total_duration_minutes,
      transfersCount: r.transfers_count,
      modes,
      legs,
      calculatedTotalFare: r.total_fare,
      hasVerifiedFaresOnly,
      highlightBadge,
    };
  });
}
