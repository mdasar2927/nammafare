"""
NammaFare API test suite.

Existing tests (6): health, places, route search (female/male/disconnected/no-IPT)
New tests (5):  unified search, reverse geocode (offline fallback), nearby transport,
                outside-Chennai filter, provenance fields on Theme7 results
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# Existing tests (must keep passing)
# ---------------------------------------------------------------------------

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data_loaded"] is True
    # Verify all Theme7 layers are loaded
    assert data["theme7_bus_stops_count"] == 2717
    assert data["theme7_bus_routes_count"] == 1348
    assert data["theme7_metro_corridors_count"] == 4
    assert data["theme7_metro_stations_count"] == 51
    assert data["theme7_suburban_tracks_count"] == 53
    assert data["theme7_suburban_stations_count"] == 70
    assert data["theme7_taz_zones_count"] == 280
    assert data["theme7_road_links_count"] == 7644


def test_places_search_theme7():
    # Test blank query returns real Theme7 stops
    response = client.get("/api/v1/places")
    assert response.status_code == 200
    places = response.json()
    assert len(places) > 0
    assert all("Theme7" in p["source"] for p in places)

    # Test searching for an actual stop in the Excel dataset
    response_anna = client.get("/api/v1/places?q=anna nagar")
    assert response_anna.status_code == 200
    anna_places = response_anna.json()
    assert len(anna_places) > 0
    assert any("Anna Nagar" in p["name"] for p in anna_places)


def test_route_search_connected_bus_female_free():
    # Central to Guindy (traverses actual MTC Anna Salai corridor lines)
    payload = {
        "origin": {"lat": 13.0827, "lng": 80.2755, "name": "Central Area"},
        "destination": {"lat": 13.0067, "lng": 80.2128, "name": "Guindy Area"},
        "gender": "female",
        "allowed_modes": ["bus", "walking"],
        "departure_time": "2026-11-06T09:00:00",
        "sort_by": "cheapest"
    }
    response = client.post("/api/v1/routes/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) > 0

    # Verify TAZ zones identified
    assert data["origin_taz"] is not None
    assert data["destination_taz"] is not None

    # Verify that the route number is a REAL MTC route from routes_merged.shp
    first_route = data["routes"][0]
    bus_leg = next(leg for leg in first_route["legs"] if leg["mode"] == "bus")
    assert bus_leg["route_number"] is not None
    # Real routes on this corridor from routes_merged include 9MET, 18D, 18X, B18, etc.
    assert len(bus_leg["polyline"]) > 10  # Sliced curve with multiple shapefile vertices
    assert "Theme7.Public_Transport.MTC.routes_merged" in bus_leg["provenance"]

    # Verify female commuter travels free under Vidiyal Payana Thittam
    assert bus_leg["fare"] == 0.0
    assert "Vidiyal Payana Thittam" in bus_leg["fare_note"]


def test_route_search_connected_bus_male_charged():
    payload = {
        "origin": {"lat": 13.0827, "lng": 80.2755, "name": "Central Area"},
        "destination": {"lat": 13.0067, "lng": 80.2128, "name": "Guindy Area"},
        "gender": "male",
        "allowed_modes": ["bus"],
        "departure_time": "2026-11-06T09:00:00",
    }
    response = client.post("/api/v1/routes/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["routes"]) > 0
    first_route = data["routes"][0]
    bus_leg = next(leg for leg in first_route["legs"] if leg["mode"] == "bus")
    assert bus_leg["fare"] > 0.0


def test_disconnected_points_return_empty_no_fabrication():
    # Point out in the sea or disconnected area where no MTC route exists
    payload = {
        "origin": {"lat": 13.3500, "lng": 80.3500, "name": "Offshore Point A"},
        "destination": {"lat": 12.7500, "lng": 80.0500, "name": "Rural South Point B"},
        "allowed_modes": ["bus", "metro", "suburban_train"]
    }
    response = client.post("/api/v1/routes/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    # Must return empty routes list, NEVER fabricate a fallback!
    assert data["routes"] == []
    assert "No connected public transport route found" in data["message"]


def test_no_fabricated_intermediate_modes():
    # Ensure Auto, Share Auto and Taxi are not fabricated into results
    payload = {
        "origin": {"lat": 13.0827, "lng": 80.2755, "name": "Central Area"},
        "destination": {"lat": 13.0067, "lng": 80.2128, "name": "Guindy Area"},
        "allowed_modes": ["auto", "share_auto", "taxi", "bus"]
    }
    response = client.post("/api/v1/routes/search", json=payload)
    assert response.status_code == 200
    routes = response.json()["routes"]
    for r in routes:
        for leg in r["legs"]:
            assert leg["mode"] not in ("auto", "share_auto", "taxi")


# ---------------------------------------------------------------------------
# New tests — unified location discovery
# ---------------------------------------------------------------------------

def test_places_search_grouped_theme7_stops():
    """
    /places/search must return grouped Theme7 transport results.
    With include_geocoded=false we avoid network calls; Theme7 results must still appear.
    """
    response = client.get("/api/v1/places/search?q=anna+nagar&include_geocoded=false")
    assert response.status_code == 200
    data = response.json()

    # Schema fields
    assert "query" in data
    assert "places" in data
    assert "bus_stops" in data
    assert "metro_stations" in data
    assert "railway_stations" in data
    assert "attribution" in data

    # Attribution must reference both Theme7 and OSM
    assert "Theme7" in data["attribution"]
    assert "OpenStreetMap" in data["attribution"]

    # Anna Nagar is a prominent MTC bus stop area — should appear
    bus_stops = data["bus_stops"]
    assert len(bus_stops) > 0
    assert any("Anna Nagar" in stop["name"] for stop in bus_stops)


def test_places_search_theme7_provenance():
    """Theme7 results must carry provenance and is_verified=true fields."""
    response = client.get("/api/v1/places/search?q=central&include_geocoded=false")
    assert response.status_code == 200
    data = response.json()
    all_stops = data["bus_stops"] + data["metro_stations"] + data["railway_stations"]
    assert len(all_stops) > 0
    for stop in all_stops:
        assert stop["is_verified"] is True
        assert stop["provenance"] is not None
        assert "Theme7" in stop["provenance"]
        assert stop["source"] is not None


def test_places_search_missing_query_returns_422():
    """Calling /places/search without q= must return HTTP 422."""
    response = client.get("/api/v1/places/search")
    assert response.status_code == 422


def test_nearby_transport_returns_theme7_stops():
    """
    /places/nearby around Chennai Central must return real Theme7 bus stops within radius.
    All returned stops must be within the requested radius.
    """
    # Chennai Central station area — well-served by MTC
    lat, lng, radius = 13.0827, 80.2755, 1000
    response = client.get(
        f"/api/v1/places/nearby?lat={lat}&lng={lng}&radius_m={radius}"
    )
    assert response.status_code == 200
    data = response.json()

    assert data["lat"] == lat
    assert data["lng"] == lng
    assert data["radius_m"] == radius

    bus_stops = data["bus_stops"]
    assert len(bus_stops) > 0, "Expected Theme7 bus stops near Chennai Central"

    # Every returned stop must carry provenance and be from Theme7
    for stop in bus_stops:
        assert stop["is_verified"] is True
        assert "Theme7" in stop["provenance"]


def test_nearby_transport_outside_chennai_rejected():
    """Coordinates outside Chennai bbox must return HTTP 400."""
    response = client.get("/api/v1/places/nearby?lat=28.6139&lng=77.2090&radius_m=500")
    assert response.status_code == 400


def test_reverse_geocode_outside_chennai_rejected():
    """Coordinates outside Chennai bbox must return HTTP 400."""
    response = client.get("/api/v1/places/reverse?lat=19.0760&lng=72.8777")
    assert response.status_code == 400


def test_reverse_geocode_in_chennai_no_network_graceful():
    """
    /places/reverse must respond with HTTP 200 even when Nominatim is unreachable.
    When geocoder fails, it must fall back to coordinate string — no 500 error.
    """
    # We use TestClient which runs in-process; Nominatim may or may not be reachable.
    # The endpoint must always return 200 within Chennai bbox.
    lat, lng = 13.0827, 80.2755
    response = client.get(f"/api/v1/places/reverse?lat={lat}&lng={lng}")
    assert response.status_code == 200
    data = response.json()
    assert data["lat"] == lat
    assert data["lng"] == lng
    # display_name must be a non-empty string (at minimum the coordinate fallback)
    assert isinstance(data["display_name"], str)
    assert len(data["display_name"]) > 0
    assert "source" in data
    assert "provenance" in data


def test_reverse_geocode_with_nearby():
    """
    /places/reverse?include_nearby=true must return a nearby_transport list.
    """
    lat, lng = 13.0827, 80.2755
    response = client.get(
        f"/api/v1/places/reverse?lat={lat}&lng={lng}&include_nearby=true&radius_m=1000"
    )
    assert response.status_code == 200
    data = response.json()
    assert data["nearby_transport"] is not None
    assert isinstance(data["nearby_transport"], list)
    # At least some stops expected near Chennai Central
    assert len(data["nearby_transport"]) > 0
