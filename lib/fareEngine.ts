import { Gender, MultimodalRoute, SortPreference } from '@/types/transit';

/**
 * Calculates dynamic route fares based on commuter gender and official Chennai transit rules.
 * Specifically handles Tamil Nadu's "Vidiyal Payana Thittam" (Free travel for women in standard MTC Ordinary buses).
 */
export function calculateRouteFareForGender(
  route: MultimodalRoute,
  gender: Gender
): MultimodalRoute {
  let updatedTotalFare = 0;

  const updatedLegs = route.legs.map((leg) => {
    let legFare = leg.fare;
    let fareNote = leg.fareNote;

    if (leg.isVidiyalEligible) {
      if (gender === 'female') {
        legFare = 0;
        fareNote = '₹0 Free travel for women under Vidiyal Payana Thittam';
      } else {
        legFare = leg.baseFareMale;
        fareNote = `₹${leg.baseFareMale} MTC Standard Stage Fare`;
      }
    }

    updatedTotalFare += legFare;

    return {
      ...leg,
      fare: legFare,
      fareNote,
    };
  });

  return {
    ...route,
    calculatedTotalFare: updatedTotalFare,
    legs: updatedLegs,
  };
}

/**
 * Recalculates and reorders an array of routes given gender and sort preference.
 */
export function processRoutes(
  routes: MultimodalRoute[],
  gender: Gender,
  sortBy: SortPreference
): MultimodalRoute[] {
  // Step 1: Recalculate fares for all routes according to gender
  const updatedRoutes = routes.map((route) => calculateRouteFareForGender(route, gender));

  // Step 2: Determine cheapest and fastest
  let minCost = Infinity;
  let minTime = Infinity;

  updatedRoutes.forEach((r) => {
    if (r.calculatedTotalFare < minCost) minCost = r.calculatedTotalFare;
    if (r.totalDurationMinutes < minTime) minTime = r.totalDurationMinutes;
  });

  // Step 3: Assign highlight badges
  const badgedRoutes = updatedRoutes.map((r) => {
    const isCheapest = r.calculatedTotalFare === minCost;
    const isFastest = r.totalDurationMinutes === minTime;

    let highlightBadge: 'Cheapest' | 'Fastest' | 'Balanced' | undefined;
    if (isCheapest && isFastest) {
      highlightBadge = 'Cheapest';
    } else if (isCheapest) {
      highlightBadge = 'Cheapest';
    } else if (isFastest) {
      highlightBadge = 'Fastest';
    } else if (r.transfersCount <= 1 && r.calculatedTotalFare <= minCost + 20) {
      highlightBadge = 'Balanced';
    }

    return {
      ...r,
      highlightBadge,
    };
  });

  // Step 4: Sort routes
  return [...badgedRoutes].sort((a, b) => {
    if (sortBy === 'cost') {
      if (a.calculatedTotalFare !== b.calculatedTotalFare) {
        return a.calculatedTotalFare - b.calculatedTotalFare;
      }
      return a.totalDurationMinutes - b.totalDurationMinutes;
    } else {
      if (a.totalDurationMinutes !== b.totalDurationMinutes) {
        return a.totalDurationMinutes - b.totalDurationMinutes;
      }
      return a.calculatedTotalFare - b.calculatedTotalFare;
    }
  });
}
