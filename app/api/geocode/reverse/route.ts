import { NextRequest, NextResponse } from 'next/server';

interface NominatimReverseResult {
  place_id: number;
  lat: string;
  lon: string;
  display_name: string;
  address?: {
    road?: string;
    suburb?: string;
    neighbourhood?: string;
    city?: string;
    town?: string;
    state_district?: string;
    amenity?: string;
    tourism?: string;
    building?: string;
  };
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const latStr = searchParams.get('lat');
  const lngStr = searchParams.get('lng');

  if (!latStr || !lngStr) {
    return NextResponse.json({ error: 'Missing coordinates' }, { status: 400 });
  }

  const lat = parseFloat(latStr);
  const lng = parseFloat(lngStr);

  if (isNaN(lat) || isNaN(lng)) {
    return NextResponse.json({ error: 'Invalid coordinates' }, { status: 400 });
  }

  try {
    const url = `https://nominatim.openstreetmap.org/reverse?format=json&addressdetails=1&zoom=18&lat=${lat}&lon=${lng}`;

    const res = await fetch(url, {
      headers: {
        'User-Agent':
          process.env.GEOCODING_USER_AGENT ||
          'NammaFare/1.0 (Chennai Multimodal Journey Planner; open-source)',
        Accept: 'application/json',
      },
      next: { revalidate: 600 },
    });

    if (!res.ok) {
      return NextResponse.json({
        name: `Selected Point (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
        displayName: `Coordinates: ${lat.toFixed(5)}, ${lng.toFixed(5)}`,
        lat,
        lng,
      });
    }

    const data: NominatimReverseResult = await res.json();
    const addr = data.address || {};
    const road = addr.road || addr.building || addr.amenity || addr.tourism;
    const suburb = addr.suburb || addr.neighbourhood || addr.city || addr.town;

    let readableName = '';
    if (road && suburb) {
      readableName = `${road}, ${suburb}`;
    } else if (road) {
      readableName = `${road}, Chennai`;
    } else if (suburb) {
      readableName = `${suburb}, Chennai`;
    } else {
      readableName = data.display_name.split(',').slice(0, 3).join(', ').trim();
    }

    return NextResponse.json({
      name: readableName || `Point (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
      displayName: data.display_name,
      lat,
      lng,
      source: 'OpenStreetMap',
    });
  } catch (error) {
    console.warn('Reverse geocoding error:', error);
    return NextResponse.json({
      name: `Point (${lat.toFixed(4)}, ${lng.toFixed(4)})`,
      displayName: `Coordinates: ${lat.toFixed(5)}, ${lng.toFixed(5)}`,
      lat,
      lng,
      source: 'Raw GPS',
    });
  }
}
