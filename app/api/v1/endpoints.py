"""
NammaFare API v1 endpoints.

Endpoints:
  GET  /api/v1/health                        — healthcheck with Theme7 layer counts
  GET  /api/v1/places                        — backward-compat: Theme7 stops + geocoded places merged as List[Place]
  GET  /api/v1/places/search                 — unified grouped search (places + bus stops + metro + rail)
  GET  /api/v1/places/reverse                — reverse geocode a coordinate
  GET  /api/v1/places/nearby                 — nearby Theme7 transport stops around a coordinate
  POST /api/v1/routes/search                 — multimodal route search

Data policy (non-negotiable):
  - Theme7 is the ONLY source for transport network routing.
  - External geocoding (Nominatim) is used ONLY for place/address discovery.
  - No mock, fabricated or hardcoded location records.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional

from app.models.schemas import (
    HealthResponse,
    Place,
    PlaceResult,
    PlacesSearchResponse,
    ReverseGeocodeResponse,
    NearbyTransportResponse,
    SearchRequest,
    SearchResponse,
)
from app.services.data_loader import TransitDataLoader
from app.services.routing_engine import MultimodalRoutingEngine
from app.services.geocoding_service import get_geocoding_provider, OSM_ATTRIBUTION
from app.core import config

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _theme7_stop_to_place_result(stop: dict, distance_m: Optional[int] = None) -> PlaceResult:
    """Convert a Theme7 stop dict to a PlaceResult."""
    desc = stop.get("description")
    if distance_m is not None:
        desc = f"{distance_m} m away" + (f" — {desc}" if desc else "")
    return PlaceResult(
        id=stop["id"],
        name=stop["name"],
        category=stop["category"],
        lat=stop["lat"],
        lng=stop["lng"],
        source=stop.get("source", "Theme7"),
        provenance=stop.get("provenance", "Theme7 dataset (organization-provided)"),
        is_verified=stop.get("is_verified", True),
        description=desc,
        display_address=None,
    )


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
def get_health():
    loader = TransitDataLoader.get_instance()
    is_loaded = len(loader.places_index) > 0
    return HealthResponse(
        status="ok",
        version="1.0.0",
        data_loaded=is_loaded,
        theme7_bus_stops_count=len(loader.bus_stops),
        theme7_bus_routes_count=len(loader.bus_routes),
        theme7_metro_corridors_count=len(loader.metro_corridors),
        theme7_metro_stations_count=len(loader.metro_stations),
        theme7_suburban_tracks_count=len(loader.suburban_tracks),
        theme7_suburban_stations_count=len(loader.suburban_stations),
        theme7_taz_zones_count=len(loader.taz_zones),
        theme7_road_links_count=len(loader.road_network),
    )


# ---------------------------------------------------------------------------
# Unified location search (new grouped endpoint)
# ---------------------------------------------------------------------------

@router.get("/places/search", response_model=PlacesSearchResponse)
def search_places_unified(
    q: str = Query(..., min_length=1, description="Location search query"),
    limit: int = Query(5, ge=1, le=20, description="Max results per category"),
    include_geocoded: bool = Query(True, description="Include Nominatim/OSM geocoded places"),
):
    """
    Unified location search returning results grouped by category:
    - places: Nominatim/OSM geocoded addresses and landmarks (Chennai only)
    - bus_stops: Theme7 MTC bus stops matching the query
    - metro_stations: Theme7 CMRL metro stations matching the query
    - railway_stations: Theme7 suburban railway stations matching the query

    Attribution: © OpenStreetMap contributors for geocoded places.
    Transport network data sourced exclusively from the Theme7 dataset.
    """
    loader = TransitDataLoader.get_instance()
    q_stripped = q.strip()

    # 1. Theme7 transport stops (locally filtered by query string)
    all_theme7 = loader.search_places(query=q_stripped, limit=limit * 6)

    bus_stops: List[PlaceResult] = []
    metro_stations: List[PlaceResult] = []
    railway_stations: List[PlaceResult] = []

    for stop in all_theme7:
        pr = _theme7_stop_to_place_result(stop)
        cat = stop.get("category", "")
        if cat == "bus_stop" and len(bus_stops) < limit:
            bus_stops.append(pr)
        elif cat == "metro_station" and len(metro_stations) < limit:
            metro_stations.append(pr)
        elif cat == "railway_station" and len(railway_stations) < limit:
            railway_stations.append(pr)

    # 2. Nominatim geocoded places (external — Chennai only)
    geocoded_places: List[PlaceResult] = []
    if include_geocoded:
        try:
            provider = get_geocoding_provider()
            raw_places = provider.search(q_stripped, limit=limit)
            for gp in raw_places:
                geocoded_places.append(
                    PlaceResult(
                        id=gp.id,
                        name=gp.name,
                        display_address=gp.display_address,
                        lat=gp.lat,
                        lng=gp.lng,
                        category="place",
                        source=gp.source,
                        provenance=gp.provenance,
                        is_verified=gp.is_verified,
                    )
                )
        except Exception:
            # Network unavailable — gracefully degrade; Theme7 results still returned
            geocoded_places = []

    return PlacesSearchResponse(
        query=q_stripped,
        places=geocoded_places,
        bus_stops=bus_stops,
        metro_stations=metro_stations,
        railway_stations=railway_stations,
        attribution=(
            "Transport network: Theme7 dataset (organization-provided). "
            + OSM_ATTRIBUTION + "."
        ),
    )


# ---------------------------------------------------------------------------
# Reverse geocoding
# ---------------------------------------------------------------------------

@router.get("/places/reverse", response_model=ReverseGeocodeResponse)
def reverse_geocode(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    include_nearby: bool = Query(False, description="Include nearby Theme7 transport stops"),
    radius_m: int = Query(500, ge=50, le=2000, description="Nearby search radius in metres"),
):
    """
    Convert GPS coordinates to a readable address using Nominatim/OSM.

    Optionally includes nearby Theme7 transport stops within *radius_m* metres.

    Important: Reverse geocoding is ONLY for human-readable address display.
    It is never used to infer transport connections.
    """
    # Validate Chennai bbox
    bb = config.CHENNAI_BBOX
    if not (bb["min_lat"] <= lat <= bb["max_lat"] and bb["min_lng"] <= lng <= bb["max_lng"]):
        raise HTTPException(
            status_code=400,
            detail="Coordinates are outside the Chennai Metropolitan Region supported by NammaFare.",
        )

    display_name = f"{round(lat, 5)}, {round(lng, 5)}"
    source = "coordinate"
    provenance = "Raw coordinate (no geocoding result)"

    try:
        provider = get_geocoding_provider()
        result = provider.reverse(lat, lng)
        if result:
            display_name = result.display_address or result.name
            source = result.source
            provenance = result.provenance
    except Exception:
        pass  # Graceful degradation — coordinate string used as fallback

    # Optional nearby transport
    nearby: Optional[List[PlaceResult]] = None
    if include_nearby:
        loader = TransitDataLoader.get_instance()
        nearby_data = loader.find_nearby_transport(lat, lng, radius_m=radius_m)
        nearby = []
        for stop, dist in nearby_data["bus_stops"]:
            nearby.append(_theme7_stop_to_place_result(stop, dist))
        for stop, dist in nearby_data["metro_stations"]:
            nearby.append(_theme7_stop_to_place_result(stop, dist))
        for stop, dist in nearby_data["railway_stations"]:
            nearby.append(_theme7_stop_to_place_result(stop, dist))

    return ReverseGeocodeResponse(
        lat=lat,
        lng=lng,
        display_name=display_name,
        source=source,
        provenance=provenance,
        nearby_transport=nearby,
    )


# ---------------------------------------------------------------------------
# Nearby transport stops
# ---------------------------------------------------------------------------

@router.get("/places/nearby", response_model=NearbyTransportResponse)
def get_nearby_transport(
    lat: float = Query(..., ge=-90, le=90, description="Latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Longitude"),
    radius_m: int = Query(
        config.NEARBY_DEFAULT_RADIUS_M, ge=50, le=5000,
        description="Search radius in metres"
    ),
):
    """
    Return Theme7 transport stops within *radius_m* metres of a coordinate.

    Results are sorted by ascending distance.
    Only data from the Theme7 dataset is returned — no geocoding, no fabrication.
    """
    bb = config.CHENNAI_BBOX
    if not (bb["min_lat"] <= lat <= bb["max_lat"] and bb["min_lng"] <= lng <= bb["max_lng"]):
        raise HTTPException(
            status_code=400,
            detail="Coordinates are outside the Chennai Metropolitan Region supported by NammaFare.",
        )

    loader = TransitDataLoader.get_instance()
    nearby_data = loader.find_nearby_transport(lat, lng, radius_m=radius_m)

    return NearbyTransportResponse(
        lat=lat,
        lng=lng,
        radius_m=radius_m,
        bus_stops=[
            _theme7_stop_to_place_result(stop, dist)
            for stop, dist in nearby_data["bus_stops"]
        ],
        metro_stations=[
            _theme7_stop_to_place_result(stop, dist)
            for stop, dist in nearby_data["metro_stations"]
        ],
        railway_stations=[
            _theme7_stop_to_place_result(stop, dist)
            for stop, dist in nearby_data["railway_stations"]
        ],
    )


# ---------------------------------------------------------------------------
# Legacy places endpoint (backward-compatible with existing frontend)
# ---------------------------------------------------------------------------

@router.get("/places", response_model=List[Place])
def get_places(
    q: Optional[str] = Query(None, description="Search query for places, stops or stations"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return"),
    include_geocoded: bool = Query(False, description="Include Nominatim/OSM results (requires network)"),
):
    """
    Backward-compatible endpoint returning a flat List[Place].

    By default returns Theme7 stops matching the query.
    Set include_geocoded=true to also include Nominatim/OSM geocoded places.
    """
    loader = TransitDataLoader.get_instance()
    q_clean = (q or "").strip()
    theme7_results = loader.search_places(query=q_clean, limit=limit)

    places: List[Place] = [
        Place(
            id=p["id"],
            name=p["name"],
            category=p["category"],
            lat=p["lat"],
            lng=p["lng"],
            source=p.get("source", "Theme7"),
            provenance=p.get("provenance", "Theme7 dataset (organization-provided)"),
            is_verified=p.get("is_verified", True),
            description=p.get("description"),
            display_address=None,
        )
        for p in theme7_results
    ]

    if include_geocoded and q_clean:
        try:
            provider = get_geocoding_provider()
            geo_results = provider.search(q_clean, limit=min(limit, config.GEOCODER_MAX_RESULTS))
            seen_ids = {p.id for p in places}
            for gp in geo_results:
                if gp.id not in seen_ids and len(places) < limit:
                    places.append(
                        Place(
                            id=gp.id,
                            name=gp.name,
                            category="place",
                            lat=gp.lat,
                            lng=gp.lng,
                            source=gp.source,
                            provenance=gp.provenance,
                            is_verified=gp.is_verified,
                            description=None,
                            display_address=gp.display_address,
                        )
                    )
        except Exception:
            pass  # Network unavailable — Theme7 results still returned

    return places


# ---------------------------------------------------------------------------
# Route search
# ---------------------------------------------------------------------------

@router.post("/routes/search", response_model=SearchResponse)
def search_routes(request: SearchRequest):
    if not (-90 <= request.origin.lat <= 90 and -180 <= request.origin.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid origin coordinates")
    if not (-90 <= request.destination.lat <= 90 and -180 <= request.destination.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid destination coordinates")

    loader = TransitDataLoader.get_instance()
    engine = MultimodalRoutingEngine(data_loader=loader)
    return engine.search_routes(request)
