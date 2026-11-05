import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "1.0.0"
    assert data["data_loaded"] is True

def test_places_search():
    # Test blank query returns default transit hubs
    response = client.get("/api/v1/places")
    assert response.status_code == 200
    places = response.json()
    assert len(places) > 0
    assert any("Central" in p["name"] for p in places)

    # Test filtered search query
    response_guindy = client.get("/api/v1/places?q=Guindy")
    assert response_guindy.status_code == 200
    guindy_places = response_guindy.json()
    assert len(guindy_places) > 0
    assert any("Guindy" in p["name"] for p in guindy_places)

def test_route_search_female_free_mtc_bus():
    # Central to Guindy
    payload = {
        "origin": {"lat": 13.0827, "lng": 80.2755, "name": "Chennai Central"},
        "destination": {"lat": 13.0067, "lng": 80.2128, "name": "Guindy"},
        "gender": "female",
        "allowed_modes": ["bus", "metro", "walking", "auto", "taxi"],
        "departure_time": "2026-11-06T09:00:00",
        "sort_by": "cheapest"
    }
    response = client.post("/api/v1/routes/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["origin"] == "Chennai Central"
    assert data["destination"] == "Guindy"
    assert len(data["routes"]) > 0

    # Verify MTC ordinary bus is FREE for female commuters
    bus_ordinary_route = next(
        (r for r in data["routes"] if "Ordinary" in r["summary"]), None
    )
    assert bus_ordinary_route is not None
    assert bus_ordinary_route["total_fare"] == 0.0
    ordinary_leg = next(leg for leg in bus_ordinary_route["legs"] if leg["mode"] == "bus")
    assert ordinary_leg["fare"] == 0.0
    assert "Vidiyal Payana Thittam" in ordinary_leg["fare_note"]

def test_route_search_male_chargeable_mtc_bus():
    # Central to Guindy
    payload = {
        "origin": {"lat": 13.0827, "lng": 80.2755, "name": "Chennai Central"},
        "destination": {"lat": 13.0067, "lng": 80.2128, "name": "Guindy"},
        "gender": "male",
        "allowed_modes": ["bus", "metro", "walking", "auto", "taxi"],
        "departure_time": "2026-11-06T09:00:00",
        "sort_by": "cheapest"
    }
    response = client.post("/api/v1/routes/search", json=payload)
    assert response.status_code == 200
    data = response.json()

    # Verify MTC ordinary bus is chargeable for male commuters
    bus_ordinary_route = next(
        (r for r in data["routes"] if "Ordinary" in r["summary"]), None
    )
    assert bus_ordinary_route is not None
    assert bus_ordinary_route["total_fare"] > 0.0
    ordinary_leg = next(leg for leg in bus_ordinary_route["legs"] if leg["mode"] == "bus")
    assert ordinary_leg["fare"] > 0.0

def test_multimodal_modes_and_sorting():
    payload = {
        "origin": {"lat": 13.0827, "lng": 80.2755, "name": "Chennai Central"},
        "destination": {"lat": 13.0067, "lng": 80.2128, "name": "Guindy"},
        "gender": "male",
        "allowed_modes": ["bus", "metro", "suburban_train", "auto", "share_auto", "taxi"],
        "sort_by": "fastest"
    }
    response = client.post("/api/v1/routes/search", json=payload)
    assert response.status_code == 200
    routes = response.json()["routes"]

    # Verify sorting by fastest
    durations = [r["total_duration_minutes"] for r in routes]
    assert durations == sorted(durations)

    # Check route modes present
    modes_present = set()
    for r in routes:
        for leg in r["legs"]:
            modes_present.add(leg["mode"])
    assert "metro" in modes_present
    assert "suburban_train" in modes_present
    assert "auto" in modes_present
    assert "taxi" in modes_present

    # Verify cheapest and fastest flags
    assert any(r["is_cheapest"] for r in routes)
    assert any(r["is_fastest"] for r in routes)

def test_invalid_coordinates():
    payload = {
        "origin": {"lat": 199.0, "lng": 80.2755, "name": "Invalid Lat"},
        "destination": {"lat": 13.0067, "lng": 80.2128, "name": "Guindy"},
    }
    response = client.post("/api/v1/routes/search", json=payload)
    assert response.status_code == 400
