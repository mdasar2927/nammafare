export type TransitMode =
  | 'walking'
  | 'mtc_bus'
  | 'metro'
  | 'suburban_train'
  | 'auto'
  | 'share_auto'
  | 'taxi';

export type Gender = 'male' | 'female';

export type SortPreference = 'cost' | 'time';

export type FareType = 'verified' | 'estimated';

export interface RouteLeg {
  id: string;
  mode: TransitMode;
  fromStop: string;
  toStop: string;
  durationMinutes: number;
  distanceMeters: number;
  fare: number;               // Current calculated fare
  baseFareMale: number;       // Original male fare
  fareType: FareType;
  routeNumber?: string;       // e.g. "18A", "21G", "570"
  serviceType?: string;       // e.g. "Ordinary (White Board)", "Deluxe", "Blue Line", "Southern Railway 2nd Class"
  isVidiyalEligible?: boolean;// Eligible for ₹0 fare for women
  fareNote?: string;
  instructions?: string;
}

export interface MultimodalRoute {
  id: string;
  source: string;
  destination: string;
  summary: string;
  totalDurationMinutes: number;
  transfersCount: number;
  modes: TransitMode[];
  legs: RouteLeg[];
  calculatedTotalFare: number;
  hasVerifiedFaresOnly: boolean;
  highlightBadge?: 'Cheapest' | 'Fastest' | 'Balanced';
}

export interface ChennaiLocation {
  id: string;
  name: string;
  tamilName?: string;
  hubType?: string;
  zone?: string;
  lat?: number;
  lng?: number;
  category?: string;
  description?: string;
}

export interface BackendPlace {
  id: string;
  name: string;
  category: string;
  lat: number;
  lng: number;
  source?: string;
  description?: string;
}

export interface BackendRouteLeg {
  mode: string;
  route_number?: string | null;
  bus_type?: string | null;
  from_name: string;
  to_name: string;
  duration_minutes: number;
  distance_meters: number;
  fare: number;
  fare_note?: string | null;
  is_estimated: boolean;
  polyline?: number[][] | null;
}

export interface BackendRouteOption {
  route_id: string;
  summary: string;
  total_fare: number;
  total_duration_minutes: number;
  total_distance_meters: number;
  transfers_count: number;
  departure_time: string;
  arrival_time: string;
  is_cheapest: boolean;
  is_fastest: boolean;
  legs: BackendRouteLeg[];
}

export interface BackendSearchResponse {
  search_id: string;
  origin: string;
  destination: string;
  departure_time: string;
  gender: string;
  routes: BackendRouteOption[];
}
