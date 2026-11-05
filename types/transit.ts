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
  baseFareMale: number;       // Original male fare (for ordinary bus recalculations)
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
  hubType: 'Metro' | 'Railway' | 'Bus Stand' | 'Locality';
  zone?: string;
}
