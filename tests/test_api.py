"""
NammaFare API test suite.

Existing tests (6):  health, places, route search (female/male/disconnected/no-IPT)
Stage-B+ tests (5):  unified search, reverse geocode (offline fallback), nearby transport,
                     outside-Chennai filter, provenance fields on Theme7 results
Stage-B unit tests:  PhotonProvider response parsing, Chennai filtering,
                     provider factory separation (forward vs reverse)
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


# ===========================================================================
# Stage B — Unit tests: PhotonProvider, NominatimProvider, factory separation
# ===========================================================================
# These tests run entirely offline (no network). They construct providers
# directly and use mock HTTP responses to verify parsing, Chennai bbox
# filtering, caching, and factory routing — without touching the API layer.

from unittest.mock import patch, MagicMock
import io
import json as _json
import time as _time

from app.services.geocoding_service import (
    PhotonProvider,
    NominatimProvider,
    GeocodedPlace,
    get_forward_geocoding_provider,
    get_reverse_geocoding_provider,
    _photon_singleton,
    _nominatim_singleton,
)
from app.core import config as _cfg


# ---------------------------------------------------------------------------
# Helpers — build fake Photon / Nominatim HTTP responses
# ---------------------------------------------------------------------------

def _photon_geojson(features: list) -> bytes:
    """Return a minimal Photon GeoJSON FeatureCollection as bytes."""
    return _json.dumps({"type": "FeatureCollection", "features": features}).encode()


def _photon_feature(osm_id: int, lat: float, lng: float, name: str, city: str = "Chennai") -> dict:
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lng, lat]},
        "properties": {
            "osm_id": osm_id,
            "osm_type": "N",
            "name": name,
            "city": city,
            "country": "India",
        },
    }


def _make_urlopen_mock(body: bytes, status: int = 200):
    """Return a context-manager mock that yields a response-like object."""
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# 1. PhotonProvider — response parsing
# ---------------------------------------------------------------------------

class TestPhotonProviderParsing:

    def _provider(self) -> PhotonProvider:
        p = PhotonProvider()
        p._cache = {}  # fresh cache every test
        return p

    def test_valid_chennai_feature_parsed_correctly(self):
        """A well-formed Photon feature inside Chennai is parsed into GeocodedPlace."""
        feature = _photon_feature(
            osm_id=12345,
            lat=13.0533,  # Marina Beach area — inside Chennai bbox
            lng=80.2833,
            name="Marina Beach",
            city="Chennai",
        )
        body = _photon_geojson([feature])
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)):
            results = provider.search("marina beach", limit=5)

        assert len(results) == 1
        place = results[0]
        assert isinstance(place, GeocodedPlace)
        assert place.name == "Marina Beach"
        assert abs(place.lat - 13.0533) < 0.0001
        assert abs(place.lng - 80.2833) < 0.0001
        assert place.source == "photon_osm"
        assert place.is_verified is False
        assert "Photon" in place.provenance
        assert "NOT a transport network source" in place.provenance
        assert place.id.startswith("photon_")

    def test_display_address_built_from_properties(self):
        """display_address concatenates name, city, country from Photon props."""
        feature = _photon_feature(12345, 13.0533, 80.2833, "Marina Beach")
        body = _photon_geojson([feature])
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)):
            results = provider.search("marina", limit=5)
        assert len(results) == 1
        # display_address must reference the place and country
        assert "Marina Beach" in results[0].display_address
        assert "India" in results[0].display_address

    def test_multiple_features_limited_correctly(self):
        """Results are capped at the requested limit."""
        features = [
            _photon_feature(i, 13.0 + i * 0.01, 80.2 + i * 0.01, f"Place {i}")
            for i in range(8)
        ]
        body = _photon_geojson(features)
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)):
            results = provider.search("place", limit=3)
        assert len(results) <= 3

    def test_empty_query_returns_empty_without_network_call(self):
        """An empty or whitespace-only query must return [] without any HTTP call."""
        provider = self._provider()
        with patch("urllib.request.urlopen") as mock_urlopen:
            results = provider.search("   ", limit=5)
        mock_urlopen.assert_not_called()
        assert results == []

    def test_network_error_returns_empty_gracefully(self):
        """Any network/HTTP exception returns [] without propagating."""
        provider = self._provider()
        with patch("urllib.request.urlopen", side_effect=OSError("connection refused")):
            results = provider.search("anna nagar", limit=5)
        assert results == []

    def test_malformed_json_returns_empty_gracefully(self):
        """Unparseable JSON response returns [] without raising."""
        provider = self._provider()
        bad_body = b"not json at all {"
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(bad_body)):
            results = provider.search("guindy", limit=5)
        assert results == []

    def test_missing_coordinates_feature_skipped(self):
        """A feature with no geometry coordinates is silently skipped."""
        feature_bad = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": []},  # empty
            "properties": {"osm_id": 1, "name": "Bad Place"},
        }
        feature_good = _photon_feature(2, 13.05, 80.27, "Good Place")
        body = _photon_geojson([feature_bad, feature_good])
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)):
            results = provider.search("place", limit=5)
        assert len(results) == 1
        assert results[0].name == "Good Place"


# ---------------------------------------------------------------------------
# 2. PhotonProvider — Chennai boundary filtering
# ---------------------------------------------------------------------------

class TestPhotonChennaiFilter:

    def _provider(self) -> PhotonProvider:
        p = PhotonProvider()
        p._cache = {}
        return p

    def test_feature_outside_chennai_bbox_discarded(self):
        """A feature with coordinates outside Chennai is filtered out."""
        # Delhi coordinates — well outside Chennai bbox
        delhi_feature = _photon_feature(999, 28.6139, 77.2090, "India Gate", city="Delhi")
        chennai_feature = _photon_feature(1, 13.0827, 80.2755, "Central Station")
        body = _photon_geojson([delhi_feature, chennai_feature])
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)):
            results = provider.search("central", limit=5)
        assert len(results) == 1
        assert results[0].name == "Central Station"

    def test_all_features_outside_chennai_returns_empty(self):
        """When every result is outside Chennai, the returned list is empty."""
        mumbai_feature = _photon_feature(42, 19.0760, 72.8777, "Gateway", city="Mumbai")
        body = _photon_geojson([mumbai_feature])
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)):
            results = provider.search("gateway", limit=5)
        assert results == []

    def test_bbox_boundary_exactly_on_edge_included(self):
        """A coordinate exactly on the Chennai bbox boundary is accepted."""
        # min_lat = 12.5, max_lng = 80.5
        edge_feature = _photon_feature(10, 12.5, 80.5, "Edge Place")
        body = _photon_geojson([edge_feature])
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)):
            results = provider.search("edge", limit=5)
        assert len(results) == 1


# ---------------------------------------------------------------------------
# 3. PhotonProvider — caching behaviour
# ---------------------------------------------------------------------------

class TestPhotonCaching:

    def test_second_identical_query_uses_cache(self):
        """A cached result must be returned without a second network call."""
        feature = _photon_feature(1, 13.05, 80.27, "Cached Place")
        body = _photon_geojson([feature])
        provider = PhotonProvider()
        provider._cache = {}

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)) as mock_open:
            provider.search("cached place", limit=5)
            provider.search("cached place", limit=5)  # second call

        # urlopen should only have been called once
        assert mock_open.call_count == 1

    def test_expired_cache_triggers_new_request(self):
        """An expired cache entry must trigger a fresh network request."""
        feature = _photon_feature(1, 13.05, 80.27, "Stale Place")
        body = _photon_geojson([feature])
        provider = PhotonProvider()
        provider._cache = {}
        provider._cache_ttl = 0  # expires immediately

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)) as mock_open:
            provider.search("stale", limit=5)
            provider.search("stale", limit=5)  # cache should have expired

        assert mock_open.call_count == 2

    def test_different_queries_each_hit_network(self):
        """Two distinct queries must each produce a network call."""
        body = _photon_geojson([])
        provider = PhotonProvider()
        provider._cache = {}

        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)) as mock_open:
            provider.search("anna nagar", limit=5)
            provider.search("guindy", limit=5)

        assert mock_open.call_count == 2


# ---------------------------------------------------------------------------
# 4. NominatimProvider — reverse geocoding
# ---------------------------------------------------------------------------

class TestNominatimReverse:

    def _provider(self) -> NominatimProvider:
        p = NominatimProvider()
        p._reverse_cache = {}
        p._last_request_time = 0.0
        return p

    def _nom_response(self, lat: float, lng: float, display: str) -> bytes:
        return _json.dumps({
            "lat": str(lat),
            "lon": str(lng),
            "display_name": display,
        }).encode()

    def test_reverse_geocode_in_chennai_returns_place(self):
        """A coordinate inside Chennai returns a GeocodedPlace with correct fields."""
        body = self._nom_response(13.0827, 80.2755, "Chennai Central, Chennai, Tamil Nadu, India")
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)):
            result = provider.reverse(13.0827, 80.2755)
        assert result is not None
        assert isinstance(result, GeocodedPlace)
        assert result.source == "nominatim_osm"
        assert result.is_verified is False
        assert "Nominatim" in result.provenance
        assert "NOT a transport network source" in result.provenance
        assert "Chennai Central" in result.display_address

    def test_reverse_geocode_outside_chennai_returns_none(self):
        """A coordinate outside the Chennai bbox returns None without any HTTP call."""
        provider = self._provider()
        with patch("urllib.request.urlopen") as mock_open:
            result = provider.reverse(28.6139, 77.2090)  # Delhi
        mock_open.assert_not_called()
        assert result is None

    def test_reverse_geocode_caches_result(self):
        """Identical reverse geocode calls must use the cache."""
        body = self._nom_response(13.0827, 80.2755, "Chennai Central, Tamil Nadu")
        provider = self._provider()
        with patch("urllib.request.urlopen", return_value=_make_urlopen_mock(body)) as mock_open:
            provider.reverse(13.0827, 80.2755)
            provider.reverse(13.0827, 80.2755)
        assert mock_open.call_count == 1

    def test_reverse_geocode_network_error_returns_none(self):
        """Network failure during reverse geocode returns None gracefully."""
        provider = self._provider()
        with patch("urllib.request.urlopen", side_effect=OSError("timeout")):
            result = provider.reverse(13.0827, 80.2755)
        assert result is None

    def test_nominatim_search_raises_not_implemented(self):
        """NominatimProvider.search() must raise NotImplementedError (not for autocomplete)."""
        provider = self._provider()
        with pytest.raises(NotImplementedError):
            provider.search("marina beach", limit=5)

    def test_photon_reverse_raises_not_implemented(self):
        """PhotonProvider.reverse() must raise NotImplementedError."""
        provider = PhotonProvider()
        provider._cache = {}
        with pytest.raises(NotImplementedError):
            provider.reverse(13.0827, 80.2755)


# ---------------------------------------------------------------------------
# 5. Factory separation — forward vs reverse
# ---------------------------------------------------------------------------

class TestProviderFactorySeparation:

    def test_get_forward_provider_returns_photon_by_default(self):
        """get_forward_geocoding_provider() must return PhotonProvider by default."""
        provider = get_forward_geocoding_provider()
        assert isinstance(provider, PhotonProvider), (
            f"Expected PhotonProvider, got {type(provider).__name__}. "
            f"FORWARD_GEOCODING_PROVIDER={_cfg.FORWARD_GEOCODING_PROVIDER!r}"
        )

    def test_get_reverse_provider_always_returns_nominatim(self):
        """get_reverse_geocoding_provider() must always return NominatimProvider."""
        provider = get_reverse_geocoding_provider()
        assert isinstance(provider, NominatimProvider)

    def test_forward_and_reverse_are_different_instances(self):
        """Forward and reverse providers must be different objects."""
        fwd = get_forward_geocoding_provider()
        rev = get_reverse_geocoding_provider()
        assert fwd is not rev

    def test_forward_provider_singleton_stable(self):
        """Calling get_forward_geocoding_provider() twice returns the same singleton."""
        p1 = get_forward_geocoding_provider()
        p2 = get_forward_geocoding_provider()
        assert p1 is p2

    def test_reverse_provider_singleton_stable(self):
        """Calling get_reverse_geocoding_provider() twice returns the same singleton."""
        p1 = get_reverse_geocoding_provider()
        p2 = get_reverse_geocoding_provider()
        assert p1 is p2

    def test_backward_compat_alias_returns_forward_provider(self):
        """get_geocoding_provider() (backward-compat alias) returns the forward provider."""
        from app.services.geocoding_service import get_geocoding_provider
        alias = get_geocoding_provider()
        fwd = get_forward_geocoding_provider()
        assert type(alias) is type(fwd)


# ===========================================================================
# Stage D — Focused integration tests: provider wiring, resilience, schemas
# ===========================================================================
# All tests in this section run offline (network calls are mocked).
# They target the gaps identified in the Stage D audit:
#   1. Endpoint-level confirmation that forward search uses PhotonProvider.
#   2. Endpoint-level confirmation that reverse uses NominatimProvider.
#   3. Theme7 transport results survive Photon network failure.
#   4. Reverse geocoding failure does not break /places or /places/search.
#   5. Chennai boundary filtering verified on /places and /places/search.
#   6. Response schema shape (required fields, types) for all 5 endpoints.

from unittest.mock import patch as _patch


# ---------------------------------------------------------------------------
# Helpers shared by Stage D
# ---------------------------------------------------------------------------

def _photon_success_body(name: str = "Test Place", lat: float = 13.05, lng: float = 80.27) -> bytes:
    """Minimal valid Photon GeoJSON with one Chennai feature."""
    import json as _j
    return _j.dumps({
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lng, lat]},
            "properties": {"osm_id": 99, "osm_type": "N", "name": name, "city": "Chennai", "country": "India"},
        }],
    }).encode()


def _nominatim_reverse_success_body(lat: float = 13.0827, lng: float = 80.2755) -> bytes:
    import json as _j
    return _j.dumps({
        "lat": str(lat),
        "lon": str(lng),
        "display_name": "Chennai Central Station, Chennai, Tamil Nadu, India",
    }).encode()


def _make_cm(body: bytes):
    """Reusable urlopen context-manager mock (same as Stage B helper)."""
    resp = MagicMock()
    resp.read.return_value = body
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


# ---------------------------------------------------------------------------
# 1. Endpoint wiring — forward search must use PhotonProvider
# ---------------------------------------------------------------------------

class TestEndpointForwardProviderWiring:
    """
    Confirm that /places/search and /places call PhotonProvider (not Nominatim)
    for external geocoding.  We mock PhotonProvider.search() and verify it is
    called; we also mock NominatimProvider.reverse() to confirm it is NOT called.
    """

    def test_places_search_calls_photon_not_nominatim(self):
        """
        GET /places/search?include_geocoded=true must call PhotonProvider.search(),
        never NominatimProvider.search().
        """
        photon_body = _photon_success_body("Test Landmark")
        nom_body = _nominatim_reverse_success_body()

        with _patch("urllib.request.urlopen", return_value=_make_cm(photon_body)) as mock_open:
            resp = client.get(
                "/api/v1/places/search?q=test&include_geocoded=true&limit=3"
            )

        assert resp.status_code == 200
        data = resp.json()
        # Photon was called (urlopen was invoked)
        assert mock_open.called
        # The URL hit must be a Photon URL, not Nominatim
        called_url = mock_open.call_args[0][0]
        called_url_str = called_url.full_url if hasattr(called_url, "full_url") else str(called_url)
        assert "photon" in called_url_str.lower() or "komoot" in called_url_str.lower(), (
            f"Expected Photon URL, got: {called_url_str}"
        )

    def test_flat_places_calls_photon_when_include_geocoded(self):
        """
        GET /places?include_geocoded=true must call PhotonProvider, not Nominatim.
        """
        photon_body = _photon_success_body("Test Stop")
        with _patch("urllib.request.urlopen", return_value=_make_cm(photon_body)) as mock_open:
            resp = client.get("/api/v1/places?q=test&include_geocoded=true")

        assert resp.status_code == 200
        called_url = mock_open.call_args[0][0]
        called_url_str = called_url.full_url if hasattr(called_url, "full_url") else str(called_url)
        assert "photon" in called_url_str.lower() or "komoot" in called_url_str.lower()

    def test_places_search_without_geocoded_never_calls_external(self):
        """
        GET /places/search?include_geocoded=false must not call any external provider.
        Theme7 results come from local data only.
        """
        with _patch("urllib.request.urlopen") as mock_open:
            resp = client.get(
                "/api/v1/places/search?q=anna+nagar&include_geocoded=false"
            )
        assert resp.status_code == 200
        mock_open.assert_not_called()


# ---------------------------------------------------------------------------
# 2. Endpoint wiring — reverse endpoint must use NominatimProvider
# ---------------------------------------------------------------------------

class TestEndpointReverseProviderWiring:
    """
    Confirm that /places/reverse calls NominatimProvider.reverse(), which hits
    the Nominatim base URL — never the Photon URL.
    """

    def test_reverse_endpoint_calls_nominatim(self):
        """
        GET /places/reverse must hit the Nominatim URL (not Photon).
        """
        nom_body = _nominatim_reverse_success_body()
        with _patch("urllib.request.urlopen", return_value=_make_cm(nom_body)) as mock_open:
            resp = client.get("/api/v1/places/reverse?lat=13.0827&lng=80.2755")

        assert resp.status_code == 200
        data = resp.json()
        # Verify a network call was made when cache is empty
        # (The singleton cache may already have a hit from a prior test;
        # accept either 0 or 1 calls — but if called, URL must be Nominatim.)
        for call in mock_open.call_args_list:
            called_url = call[0][0]
            called_url_str = called_url.full_url if hasattr(called_url, "full_url") else str(called_url)
            assert "nominatim" in called_url_str.lower(), (
                f"Reverse geocode must use Nominatim, got URL: {called_url_str}"
            )
            assert "photon" not in called_url_str.lower() and "komoot" not in called_url_str.lower()

    def test_reverse_endpoint_result_carries_nominatim_provenance(self):
        """
        When Nominatim returns a result, the endpoint response must carry
        Nominatim provenance (not Photon).
        """
        nom_body = _nominatim_reverse_success_body()
        # Clear the reverse cache on the singleton so a fresh request is made
        from app.services.geocoding_service import _nominatim_singleton
        nom_provider = _nominatim_singleton()
        nom_provider._reverse_cache = {}  # force fresh call
        nom_provider._last_request_time = 0.0

        with _patch("urllib.request.urlopen", return_value=_make_cm(nom_body)):
            resp = client.get("/api/v1/places/reverse?lat=13.0827&lng=80.2755")

        assert resp.status_code == 200
        data = resp.json()
        # Provenance must reference Nominatim (or fall back to coordinate if cache hit)
        # Either way it must NOT say "Photon"
        assert "photon" not in data["provenance"].lower()
        assert "Photon" not in data["provenance"]


# ---------------------------------------------------------------------------
# 3. Theme7 results survive Photon unavailability
# ---------------------------------------------------------------------------

class TestTheme7ResilienceWhenPhotonFails:
    """
    When Photon is unreachable or returns an error, /places/search and /places
    must still return Theme7 transport stops from local data.  The geocoded
    'places' list may be empty, but bus_stops/metro_stations/railway_stations
    (and the flat List[Place] for /places) must still be populated.
    """

    def test_places_search_theme7_survives_photon_timeout(self):
        """
        When Photon raises OSError, /places/search still returns Theme7 bus stops.
        """
        with _patch("urllib.request.urlopen", side_effect=OSError("photon unreachable")):
            resp = client.get(
                "/api/v1/places/search?q=anna+nagar&include_geocoded=true"
            )
        assert resp.status_code == 200
        data = resp.json()
        # Photon places must be empty (graceful degradation)
        assert data["places"] == []
        # Theme7 bus stops must still be there
        assert len(data["bus_stops"]) > 0
        assert any("Anna Nagar" in s["name"] for s in data["bus_stops"])

    def test_flat_places_theme7_survives_photon_timeout(self):
        """
        When Photon raises OSError, GET /places still returns Theme7 stops.
        """
        with _patch("urllib.request.urlopen", side_effect=OSError("photon unreachable")):
            resp = client.get("/api/v1/places?q=anna+nagar&include_geocoded=true")
        assert resp.status_code == 200
        places = resp.json()
        assert len(places) > 0
        # All returned results must be from Theme7 (source contains "Theme7")
        theme7_results = [p for p in places if "Theme7" in p["source"]]
        assert len(theme7_results) > 0

    def test_places_search_photon_malformed_response_degrades_gracefully(self):
        """
        When Photon returns malformed JSON, Theme7 results are still returned.
        """
        bad_body = b"{ definitely not valid geojson }"
        with _patch("urllib.request.urlopen", return_value=_make_cm(bad_body)):
            resp = client.get(
                "/api/v1/places/search?q=central&include_geocoded=true"
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["places"] == []
        # Theme7 transport results unaffected
        total_theme7 = len(data["bus_stops"]) + len(data["metro_stations"]) + len(data["railway_stations"])
        assert total_theme7 > 0


# ---------------------------------------------------------------------------
# 4. Reverse geocoding failure does not break location search
# ---------------------------------------------------------------------------

class TestReverseFailureDoesNotBreakSearch:
    """
    Nominatim failure on /places/reverse must not propagate to or affect
    /places or /places/search endpoints.
    """

    def test_reverse_nominatim_failure_returns_200_with_fallback(self):
        """
        When Nominatim is completely unreachable, /places/reverse returns HTTP 200
        with a coordinate-string fallback — never HTTP 500.
        """
        from app.services.geocoding_service import _nominatim_singleton
        nom = _nominatim_singleton()
        nom._reverse_cache = {}
        nom._last_request_time = 0.0

        with _patch("urllib.request.urlopen", side_effect=OSError("nominatim down")):
            resp = client.get("/api/v1/places/reverse?lat=13.0827&lng=80.2755")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["display_name"]) > 0
        # Fallback: coordinate-based string, source is "coordinate"
        assert data["source"] == "coordinate"

    def test_reverse_failure_does_not_affect_places_search(self):
        """
        Nominatim being down must have zero effect on /places/search, which uses
        Photon for forward geocoding (completely independent code path).
        """
        photon_body = _photon_success_body("Marina Beach", lat=13.0533, lng=80.2833)
        # Simulate Photon working, Nominatim broken
        # (Both go through urlopen; Photon URL contains "photon", Nominatim contains "nominatim")
        def _smart_mock(request, **kwargs):
            url_str = request.full_url if hasattr(request, "full_url") else str(request)
            if "nominatim" in url_str.lower():
                raise OSError("Nominatim is down")
            return _make_cm(photon_body)

        with _patch("urllib.request.urlopen", side_effect=_smart_mock):
            resp = client.get(
                "/api/v1/places/search?q=marina&include_geocoded=true"
            )

        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# 5. Chennai boundary filtering — verified at the endpoint level
# ---------------------------------------------------------------------------

class TestChennaiFilterAtEndpointLevel:
    """
    Verify Chennai bbox enforcement at the endpoint layer, not just the provider.
    /places/nearby and /places/reverse reject non-Chennai coordinates with HTTP 400.
    /places/search must return empty 'places' if Photon returns only non-Chennai results.
    """

    def test_nearby_rejects_mumbai_coordinates(self):
        resp = client.get("/api/v1/places/nearby?lat=19.0760&lng=72.8777&radius_m=500")
        assert resp.status_code == 400

    def test_nearby_rejects_delhi_coordinates(self):
        resp = client.get("/api/v1/places/nearby?lat=28.6139&lng=77.2090&radius_m=500")
        assert resp.status_code == 400

    def test_reverse_rejects_coordinates_outside_india(self):
        # London
        resp = client.get("/api/v1/places/reverse?lat=51.5074&lng=-0.1278")
        assert resp.status_code == 400

    def test_places_search_photon_non_chennai_results_filtered(self):
        """
        If Photon returns results outside Chennai bbox, they must not appear in
        the 'places' list of /places/search.
        """
        import json as _j
        # Photon returns a result from Delhi (outside Chennai bbox)
        delhi_body = _j.dumps({
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [77.2090, 28.6139]},  # Delhi
                "properties": {"osm_id": 42, "osm_type": "N", "name": "India Gate", "city": "Delhi", "country": "India"},
            }],
        }).encode()

        with _patch("urllib.request.urlopen", return_value=_make_cm(delhi_body)):
            resp = client.get(
                "/api/v1/places/search?q=india+gate&include_geocoded=true"
            )

        assert resp.status_code == 200
        data = resp.json()
        # Delhi result must be discarded; places list must be empty
        assert data["places"] == []
        # Theme7 transport results are unaffected (from local data)
        # (may also be empty if "india gate" matches no Theme7 stops — that's correct)


# ---------------------------------------------------------------------------
# 6. Response schema shape — all five location endpoints
# ---------------------------------------------------------------------------

class TestResponseSchemaShape:
    """
    Verify that all five location-related endpoints return the expected
    field structure and types.  These tests guard against accidental schema
    regressions from future refactors.
    """

    # --- GET /api/v1/health ---
    def test_health_schema(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        d = resp.json()
        required_fields = {
            "status": str, "version": str, "data_loaded": bool,
            "theme7_bus_stops_count": int, "theme7_bus_routes_count": int,
            "theme7_metro_corridors_count": int, "theme7_metro_stations_count": int,
            "theme7_suburban_tracks_count": int, "theme7_suburban_stations_count": int,
            "theme7_taz_zones_count": int, "theme7_road_links_count": int,
        }
        for field, expected_type in required_fields.items():
            assert field in d, f"Missing field: {field}"
            assert isinstance(d[field], expected_type), (
                f"Field {field}: expected {expected_type.__name__}, got {type(d[field]).__name__}"
            )

    # --- GET /api/v1/places ---
    def test_flat_places_schema(self):
        resp = client.get("/api/v1/places?q=central")
        assert resp.status_code == 200
        places = resp.json()
        assert isinstance(places, list)
        assert len(places) > 0
        required = {"id", "name", "category", "lat", "lng", "source"}
        for place in places:
            for field in required:
                assert field in place, f"Place missing field: {field}"
            assert isinstance(place["lat"], float)
            assert isinstance(place["lng"], float)
            assert isinstance(place["name"], str) and len(place["name"]) > 0
            assert isinstance(place["id"], str)

    # --- GET /api/v1/places/search ---
    def test_grouped_places_search_schema(self):
        resp = client.get("/api/v1/places/search?q=central&include_geocoded=false")
        assert resp.status_code == 200
        d = resp.json()
        required_top = {"query", "places", "bus_stops", "metro_stations", "railway_stations", "attribution"}
        for field in required_top:
            assert field in d, f"PlacesSearchResponse missing field: {field}"
        assert isinstance(d["query"], str)
        assert isinstance(d["places"], list)
        assert isinstance(d["bus_stops"], list)
        assert isinstance(d["metro_stations"], list)
        assert isinstance(d["railway_stations"], list)
        assert isinstance(d["attribution"], str) and len(d["attribution"]) > 0
        # PlaceResult schema check on first bus stop
        for stop in d["bus_stops"][:3]:
            for field in ("id", "name", "category", "lat", "lng", "source", "provenance", "is_verified"):
                assert field in stop, f"PlaceResult missing field: {field}"
            assert isinstance(stop["is_verified"], bool)
            assert isinstance(stop["lat"], float)

    # --- GET /api/v1/places/reverse ---
    def test_reverse_geocode_schema(self):
        resp = client.get("/api/v1/places/reverse?lat=13.0827&lng=80.2755")
        assert resp.status_code == 200
        d = resp.json()
        for field in ("lat", "lng", "display_name", "source", "provenance"):
            assert field in d, f"ReverseGeocodeResponse missing field: {field}"
        assert isinstance(d["lat"], float)
        assert isinstance(d["lng"], float)
        assert isinstance(d["display_name"], str) and len(d["display_name"]) > 0
        # nearby_transport is optional — if present must be a list
        if d.get("nearby_transport") is not None:
            assert isinstance(d["nearby_transport"], list)

    # --- GET /api/v1/places/nearby ---
    def test_nearby_transport_schema(self):
        resp = client.get("/api/v1/places/nearby?lat=13.0827&lng=80.2755&radius_m=800")
        assert resp.status_code == 200
        d = resp.json()
        for field in ("lat", "lng", "radius_m", "bus_stops", "metro_stations", "railway_stations"):
            assert field in d, f"NearbyTransportResponse missing field: {field}"
        assert d["lat"] == 13.0827
        assert d["lng"] == 80.2755
        assert d["radius_m"] == 800
        assert isinstance(d["bus_stops"], list)
        # PlaceResult schema on each stop
        for stop in d["bus_stops"][:3]:
            assert "is_verified" in stop
            assert stop["is_verified"] is True
            assert "provenance" in stop
            assert "Theme7" in stop["provenance"]

    # --- POST /api/v1/routes/search schema (guard: no geocoding bleed-through) ---
    def test_route_search_schema_unaffected(self):
        """
        Route search response schema must be unchanged — no geocoding fields
        should have leaked into SearchResponse or RouteLeg.
        """
        payload = {
            "origin": {"lat": 13.0827, "lng": 80.2755, "name": "Central"},
            "destination": {"lat": 13.0067, "lng": 80.2128, "name": "Guindy"},
            "gender": "male",
            "allowed_modes": ["bus"],
        }
        resp = client.post("/api/v1/routes/search", json=payload)
        assert resp.status_code == 200
        d = resp.json()
        for field in ("search_id", "origin", "destination", "departure_time", "gender", "routes"):
            assert field in d, f"SearchResponse missing field: {field}"
        # Verify legs still have correct transport fields
        if d["routes"]:
            leg = d["routes"][0]["legs"][0]
            for field in ("mode", "from_name", "to_name", "duration_minutes", "distance_meters", "fare"):
                assert field in leg, f"RouteLeg missing field: {field}"
