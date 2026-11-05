import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

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
