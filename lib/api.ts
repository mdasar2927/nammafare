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

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Check backend health status and loaded Theme7 layers
 */
export async function fetchHealth(): Promise<{
  status: string;
  version: string;
  data_loaded: boolean;
  theme7_bus_stops_count?: number;
  theme7_bus_routes_count?: number;
  theme7_metro_corridors_count?: number;
  theme7_metro_stations_count?: number;
  theme7_suburban_tracks_count?: number;
  theme7_suburban_stations_count?: number;
  theme7_taz_zones_count?: number;
} | null> {
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
 * Fetch autocomplete suggestions for actual Theme7 places, stations and stops
 */
export async function fetchPlaces(query: string, limit = 8): Promise<ChennaiLocation[]> {
  try {
    const url = query.trim()
      ? `${API_BASE_URL}/api/v1/places?q=${encodeURIComponent(query.trim())}&limit=${limit}`
      : `${API_BASE_URL}/api/v1/places?limit=${limit}`;

    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error(`Places API responded with ${res.status}`);
    const places: BackendPlace[] = await res.json();

    if (places && places.length > 0) {
      return places.map((p) => {
        let hubType = 'Stop';
        if (p.category === 'interchange') hubType = 'Interchange';
        else if (p.category === 'metro_station') hubType = 'Metro';
        else if (p.category === 'railway_station') hubType = 'Suburban Rail';
        else if (p.category === 'bus_stop') hubType = 'MTC Bus Stop';

        return {
          id: p.id,
          name: p.name,
          category: p.category,
          hubType,
          lat: p.lat,
          lng: p.lng,
          source: p.source || 'Theme7',
          description: p.description,
        };
      });
    }
    return [];
  } catch (err) {
    console.warn('Places fetch error:', err);
    return [];
  }
}

/**
 * Resolve coordinates for a given place name using actual Theme7 places index
 */
export async function resolveCoordinates(
  placeName: string
): Promise<{ lat: number; lng: number } | null> {
  try {
    const places = await fetchPlaces(placeName, 1);
    if (places && places.length > 0 && typeof places[0].lat === 'number' && typeof places[0].lng === 'number') {
      return { lat: places[0].lat, lng: places[0].lng };
    }
  } catch {
    // handled below
  }
  return null;
}

/**
 * Map backend mode string to supported TransitMode (only walking, mtc_bus, metro, suburban_train)
 */
function mapBackendMode(mode: string): TransitMode {
  const m = mode.toLowerCase().trim();
  if (m === 'bus') return 'mtc_bus';
  if (m === 'metro') return 'metro';
  if (m === 'suburban_train') return 'suburban_train';
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

export interface SearchRoutesResult {
  routes: MultimodalRoute[];
  message?: string | null;
  originTaz?: string | null;
  destTaz?: string | null;
}

/**
 * Execute route search against the FastAPI backend with strict no-mock policy
 */
export async function searchRoutesApi(
  params: SearchRoutesParams
): Promise<SearchRoutesResult> {
  const { source, destination, gender, sortBy } = params;

  // Resolve coordinates from input or backend places index
  const originCoords =
    params.sourceCoords && params.sourceCoords.lat && params.sourceCoords.lng
      ? params.sourceCoords
      : await resolveCoordinates(source);

  const destinationCoords =
    params.destCoords && params.destCoords.lat && params.destCoords.lng
      ? params.destCoords
      : await resolveCoordinates(destination);

  if (!originCoords || !destinationCoords) {
    return {
      routes: [],
      message: `Could not determine geospatial coordinates for "${!originCoords ? source : destination}". Please select a location from the autocomplete list.`,
    };
  }

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
    return {
      routes: [],
      message: data.message || 'No connected public transport route found between these locations in Theme7 network.',
      originTaz: data.origin_taz,
      destTaz: data.destination_taz,
    };
  }

  // Convert backend RouteOption[] to frontend MultimodalRoute[]
  const mappedRoutes: MultimodalRoute[] = data.routes.map((r) => {
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
        serviceType = 'Chennai Metro Rail';
      } else if (mode === 'walking') {
        serviceType = 'Pedestrian Transfer';
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
        fareType: leg.is_verified ? 'verified' : 'estimated',
        isVerified: leg.is_verified,
        provenance: leg.provenance || undefined,
        routeNumber: leg.route_number || undefined,
        serviceType,
        isVidiyalEligible,
        fareNote: leg.fare_note || undefined,
        instructions: `${leg.from_name} ➔ ${leg.to_name}`,
        polyline: leg.polyline || undefined,
      };
    });

    const modes = Array.from(new Set(legs.map((l) => l.mode)));
    const hasVerifiedFaresOnly = !legs.some((l) => !l.isVerified);

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
      isVerified: r.is_verified,
      provenance: r.provenance || undefined,
      highlightBadge,
    };
  });

  return {
    routes: mappedRoutes,
    message: data.message,
    originTaz: data.origin_taz,
    destTaz: data.destination_taz,
  };
}
