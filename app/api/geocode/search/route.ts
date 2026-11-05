import { NextRequest, NextResponse } from 'next/server';

interface NominatimResult {
  place_id: number;
  osm_id: number;
  lat: string;
  lon: string;
  display_name: string;
  type: string;
  class: string;
  address?: {
    road?: string;
    suburb?: string;
    neighbourhood?: string;
    city?: string;
    town?: string;
    state_district?: string;
    state?: string;
    amenity?: string;
    tourism?: string;
  };
}

// In-memory micro-cache for autocomplete queries
const searchCache = new Map<string, { timestamp: number; data: any }>();
const CACHE_TTL_MS = 60 * 1000; // 1 minute

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get('q')?.trim() || '';

  if (!q || q.length < 2) {
    return NextResponse.json([]);
  }

  const cacheKey = q.toLowerCase();
  const cached = searchCache.get(cacheKey);
  if (cached && Date.now() - cached.timestamp < CACHE_TTL_MS) {
    return NextResponse.json(cached.data);
  }

  try {
    // Chennai Bounding Box: 79.85°E to 80.40°E, 12.75°N to 13.35°N
    const nominatimUrl = `https://nominatim.openstreetmap.org/search?format=json&addressdetails=1&viewbox=79.85,13.35,80.40,12.75&bounded=1&limit=6&q=${encodeURIComponent(
      q + ', Chennai'
    )}`;

    const res = await fetch(nominatimUrl, {
      headers: {
        'User-Agent':
          process.env.GEOCODING_USER_AGENT ||
          'NammaFare/1.0 (Chennai Multimodal Journey Planner; open-source)',
        Accept: 'application/json',
      },
      next: { revalidate: 300 },
    });

    if (!res.ok) {
      console.warn(`Nominatim search responded with status ${res.status}`);
      return NextResponse.json([]);
    }

    const items: NominatimResult[] = await res.json();

    const formatted = items.map((item) => {
      const road = item.address?.road;
      const suburb = item.address?.suburb || item.address?.neighbourhood;
      const name = item.address?.amenity || item.address?.tourism || road || item.display_name.split(',')[0].trim();
      const area = suburb ? `${suburb}, Chennai` : 'Chennai';

      return {
        id: `osm-${item.place_id}`,
        name: name !== area ? `${name}, ${area}` : item.display_name.split(',').slice(0, 3).join(', ').trim(),
        category: item.type === 'station' || item.class === 'railway' ? 'Transit Landmark' : 'Landmark / Address',
        lat: parseFloat(item.lat),
        lng: parseFloat(item.lon),
        source: 'OpenStreetMap',
        description: item.display_name.split(',').slice(1, 4).join(', ').trim(),
      };
    });

    searchCache.set(cacheKey, { timestamp: Date.now(), data: formatted });
    return NextResponse.json(formatted);
  } catch (error) {
    console.error('Geocode search error:', error);
    return NextResponse.json([]);
  }
}
