"""
Geocoding service with separate forward (autocomplete) and reverse providers.

Architectural split:
  - Forward geocoding / autocomplete  →  PhotonProvider
      Photon is designed for typeahead; no per-request rate-limit policy violation.
  - Reverse geocoding                 →  NominatimProvider
      Nominatim permits single-coordinate reverse lookups triggered by user action.
      Nominatim usage policy FORBIDS autocomplete/typeahead — it is never used for search.

External geocoders are used ONLY for place/address discovery.
They must NEVER be used to infer transport routes or connections.
All results carry explicit source, provenance and is_verified labels.
"""

import abc
import json
import logging
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from app.core import config

logger = logging.getLogger(__name__)

# Attribution string required by Nominatim / OSM usage policy (also covers Photon)
OSM_ATTRIBUTION = "Places/addresses: \u00a9 OpenStreetMap contributors (ODbL)"


# ---------------------------------------------------------------------------
# Shared data structure
# ---------------------------------------------------------------------------

class GeocodedPlace:
    """A geocoded place/address result from an external provider."""

    __slots__ = (
        "id", "name", "display_address", "lat", "lng",
        "category", "source", "provenance", "is_verified",
    )

    def __init__(
        self,
        *,
        id: str,
        name: str,
        display_address: str,
        lat: float,
        lng: float,
        category: str = "place",
        source: str,
        provenance: str,
        is_verified: bool = False,
    ):
        self.id = id
        self.name = name
        self.display_address = display_address
        self.lat = lat
        self.lng = lng
        self.category = category
        self.source = source
        self.provenance = provenance
        self.is_verified = is_verified

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "display_address": self.display_address,
            "lat": self.lat,
            "lng": self.lng,
            "category": self.category,
            "source": self.source,
            "provenance": self.provenance,
            "is_verified": self.is_verified,
        }


# ---------------------------------------------------------------------------
# Abstract base class
# ---------------------------------------------------------------------------

class GeocodingProvider(abc.ABC):
    """Abstract geocoding provider. Implementations must be thread-safe."""

    @abc.abstractmethod
    def search(self, query: str, limit: int = 5) -> List[GeocodedPlace]:
        """Forward geocode: return Chennai-filtered places matching *query*."""

    @abc.abstractmethod
    def reverse(self, lat: float, lng: float) -> Optional[GeocodedPlace]:
        """Reverse geocode a coordinate to a human-readable place."""


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _in_chennai(lat: float, lng: float) -> bool:
    """Return True when the coordinate falls inside the Chennai Metropolitan bbox."""
    bb = config.CHENNAI_BBOX
    return (
        bb["min_lat"] <= lat <= bb["max_lat"]
        and bb["min_lng"] <= lng <= bb["max_lng"]
    )


# Sentinel that distinguishes "not in cache" from "cached None result"
_SENTINEL = object()


# ---------------------------------------------------------------------------
# PhotonProvider — forward geocoding / autocomplete
# ---------------------------------------------------------------------------

class PhotonProvider(GeocodingProvider):
    """
    Photon (https://photon.komoot.io) forward-geocoding provider.

    Photon is built for autocomplete/typeahead; it uses OSM data and is
    designed to handle high-frequency prefix queries without violating any
    usage policy (unlike Nominatim, which explicitly prohibits typeahead).

    Usage notes:
    - Base URL is configurable via PHOTON_BASE_URL env var so the app can
      switch to a self-hosted instance with zero code changes.
    - In-memory TTL cache (PHOTON_CACHE_TTL seconds, default 5 min) reduces
      load on the public demo API.
    - Hard timeout (PHOTON_TIMEOUT seconds, default 5) prevents slow external
      calls from blocking API responses.
    - Results are filtered to the Chennai bounding box after fetching.
    - On any network error, the method returns an empty list (graceful degradation).
    - reverse() raises NotImplementedError — Photon reverse is not used; use
      NominatimProvider for reverse geocoding.
    """

    def __init__(self):
        self._base_url = config.PHOTON_BASE_URL.rstrip("/")
        self._timeout = config.PHOTON_TIMEOUT
        self._cache_ttl = config.PHOTON_CACHE_TTL
        self._max_results = config.PHOTON_MAX_RESULTS
        # cache: (query_lower, limit) -> (timestamp, List[GeocodedPlace])
        self._cache: Dict[Tuple, Tuple[float, List[GeocodedPlace]]] = {}

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _cache_get(self, key: Tuple) -> Optional[List[GeocodedPlace]]:
        entry = self._cache.get(key)
        if entry and (time.monotonic() - entry[0]) < self._cache_ttl:
            return entry[1]
        return None

    def _cache_set(self, key: Tuple, value: List[GeocodedPlace]) -> None:
        self._cache[key] = (time.monotonic(), value)

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> Any:
        """GET *url* and return parsed JSON, or None on any error."""
        req = urllib.request.Request(
            url,
            headers={"Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("Photon request failed for %s: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _build_display_address(props: Dict[str, Any]) -> str:
        """Construct a human-readable address string from Photon properties."""
        parts = []
        # Prefer the most specific name fields
        for key in ("name", "street", "housenumber"):
            val = props.get(key)
            if val:
                parts.append(str(val))
        for key in ("district", "city", "county", "state"):
            val = props.get(key)
            if val and val not in parts:
                parts.append(str(val))
        if "country" in props:
            parts.append(str(props["country"]))
        return ", ".join(parts) if parts else ""

    @staticmethod
    def _short_name(props: Dict[str, Any]) -> str:
        """Return the most specific short name from Photon properties."""
        # Prefer explicit name, fall back to street, then city
        for key in ("name", "street", "city", "district"):
            val = props.get(key)
            if val:
                return str(val)
        return ""

    def _parse_feature(self, feature: Dict[str, Any], query: str) -> Optional[GeocodedPlace]:
        """
        Parse one GeoJSON feature from Photon into a GeocodedPlace.
        Returns None if the feature is outside the Chennai bbox or malformed.
        """
        try:
            geom = feature.get("geometry", {})
            coords = geom.get("coordinates", [])
            if len(coords) < 2:
                return None
            lng, lat = float(coords[0]), float(coords[1])

            if not _in_chennai(lat, lng):
                return None

            props = feature.get("properties", {})
            osm_id = str(props.get("osm_id", ""))
            osm_type = str(props.get("osm_type", "N"))  # N/W/R
            short = self._short_name(props) or query
            display = self._build_display_address(props) or short

            return GeocodedPlace(
                id=f"photon_{osm_type}{osm_id}",
                name=short,
                display_address=display,
                lat=lat,
                lng=lng,
                category="place",
                source="photon_osm",
                provenance=(
                    "Photon/OSM (external forward geocoder) — "
                    "NOT a transport network source"
                ),
                is_verified=False,
            )
        except (KeyError, ValueError, TypeError, IndexError):
            return None

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 5) -> List[GeocodedPlace]:
        """
        Autocomplete search via Photon.

        Results are:
          - Filtered to the Chennai bounding box.
          - Cached for PHOTON_CACHE_TTL seconds to reduce external load.
          - Capped at *limit* results.
          - Returned as an empty list on any network/parse failure.
        """
        query = query.strip()
        if not query:
            return []

        # Respect the caller's limit but never fetch more than PHOTON_MAX_RESULTS
        fetch_count = min(max(limit * 2, 5), self._max_results)
        key = (query.lower(), limit)
        cached = self._cache_get(key)
        if cached is not None:
            return cached

        # Bias toward Chennai by appending it when not already present
        biased_query = query if "chennai" in query.lower() else f"{query} Chennai"

        params = urllib.parse.urlencode(
            {
                "q": biased_query,
                "limit": fetch_count,
                # Photon bbox: lon_min,lat_min,lon_max,lat_max
                "bbox": config.PHOTON_BBOX,
                "lang": "en",
            }
        )
        url = f"{self._base_url}/api?{params}"
        raw = self._get_json(url)

        results: List[GeocodedPlace] = []
        if raw and isinstance(raw, dict):
            features = raw.get("features", [])
            for feature in features:
                place = self._parse_feature(feature, query)
                if place is not None:
                    results.append(place)
                if len(results) >= limit:
                    break

        self._cache_set(key, results)
        return results

    def reverse(self, lat: float, lng: float) -> Optional[GeocodedPlace]:
        """
        Not supported by this provider.
        Use get_reverse_geocoding_provider() (NominatimProvider) instead.
        """
        raise NotImplementedError(
            "PhotonProvider does not support reverse geocoding. "
            "Use get_reverse_geocoding_provider() to obtain NominatimProvider."
        )


# ---------------------------------------------------------------------------
# NominatimProvider — reverse geocoding ONLY
# ---------------------------------------------------------------------------

class NominatimProvider(GeocodingProvider):
    """
    Nominatim (OpenStreetMap) provider — used exclusively for REVERSE geocoding.

    Nominatim usage policy compliance:
    - Autocomplete/typeahead is explicitly PROHIBITED by the usage policy.
      This class therefore has NO forward-search use in production.
    - Maximum 1 request per second (enforced via _last_request_time).
    - Identifying User-Agent header required (set via NOMINATIM_USER_AGENT).
    - In-memory TTL cache (NOMINATIM_CACHE_TTL seconds, default 10 min).
    - Results filtered to Chennai bounding box.
    - Attribution: © OpenStreetMap contributors.
    """

    def __init__(self):
        self._base_url = config.NOMINATIM_BASE_URL.rstrip("/")
        self._user_agent = config.NOMINATIM_USER_AGENT
        self._timeout = config.NOMINATIM_TIMEOUT
        self._cache_ttl = config.NOMINATIM_CACHE_TTL
        # reverse cache: (lat5, lng5) -> (timestamp, Optional[GeocodedPlace])
        self._reverse_cache: Dict[Tuple, Tuple[float, Any]] = {}
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Rate limiting (1 req/s — Nominatim usage policy)
    # ------------------------------------------------------------------

    def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        wait = 1.0 - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.monotonic()

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> Any:
        """GET *url* with the required User-Agent header; return JSON or None."""
        self._rate_limit()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("Nominatim request failed for %s: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _reverse_cache_get(self, key: Tuple) -> Any:
        """Return cached value or _SENTINEL when not cached / expired."""
        entry = self._reverse_cache.get(key)
        if entry and (time.monotonic() - entry[0]) < self._cache_ttl:
            return entry[1]  # may legitimately be None
        return _SENTINEL

    def _reverse_cache_set(self, key: Tuple, value: Optional[GeocodedPlace]) -> None:
        self._reverse_cache[key] = (time.monotonic(), value)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 5) -> List[GeocodedPlace]:
        """
        Nominatim forward search is intentionally not used in production.
        It is retained here only so unit tests can inject NominatimProvider
        directly when needed. The public autocomplete path always uses
        PhotonProvider via get_forward_geocoding_provider().
        """
        # This path MUST NOT be called on every keystroke.
        # It is included solely for test/diagnostic purposes.
        raise NotImplementedError(
            "NominatimProvider.search() is not for production autocomplete. "
            "Nominatim usage policy prohibits typeahead. "
            "Use get_forward_geocoding_provider() (PhotonProvider) instead."
        )

    def reverse(self, lat: float, lng: float) -> Optional[GeocodedPlace]:
        """
        Reverse-geocode a coordinate to a human-readable address.

        Only called on explicit user action (e.g. pin drop), never during
        continuous input or map panning.
        Results are cached (NOMINATIM_CACHE_TTL seconds) and rate-limited
        to 1 request per second per process.
        """
        if not _in_chennai(lat, lng):
            return None

        key = (round(lat, 5), round(lng, 5))
        cached = self._reverse_cache_get(key)
        if cached is not _SENTINEL:
            return cached  # may be None (cached "no result")

        params = urllib.parse.urlencode(
            {
                "lat": lat,
                "lon": lng,
                "format": "jsonv2",
                "addressdetails": "1",
                "zoom": "18",
            }
        )
        url = f"{self._base_url}/reverse?{params}"
        raw = self._get_json(url)

        result: Optional[GeocodedPlace] = None
        if raw and isinstance(raw, dict) and "lat" in raw:
            try:
                rlat = float(raw["lat"])
                rlng = float(raw["lon"])
                display = raw.get("display_name", f"{lat},{lng}")
                short_name = display.split(",")[0].strip()
                result = GeocodedPlace(
                    id=f"nom_rev_{round(lat, 5)}_{round(lng, 5)}",
                    name=short_name,
                    display_address=display,
                    lat=rlat,
                    lng=rlng,
                    category="place",
                    source="nominatim_osm",
                    provenance=(
                        "Nominatim/OSM reverse geocode (external) — "
                        "NOT a transport network source"
                    ),
                    is_verified=False,
                )
            except (KeyError, ValueError, TypeError):
                result = None

        self._reverse_cache_set(key, result)
        return result


# ---------------------------------------------------------------------------
# Provider singletons (one instance per process)
# ---------------------------------------------------------------------------

_photon_instance: Optional[PhotonProvider] = None
_nominatim_instance: Optional[NominatimProvider] = None


def _photon_singleton() -> PhotonProvider:
    global _photon_instance
    if _photon_instance is None:
        _photon_instance = PhotonProvider()
    return _photon_instance


def _nominatim_singleton() -> NominatimProvider:
    global _nominatim_instance
    if _nominatim_instance is None:
        _nominatim_instance = NominatimProvider()
    return _nominatim_instance


# ---------------------------------------------------------------------------
# Public factory functions
# ---------------------------------------------------------------------------

def get_forward_geocoding_provider() -> GeocodingProvider:
    """
    Return the configured forward-geocoding (autocomplete) provider.

    Default: PhotonProvider (autocomplete-safe, OSM-based).
    Override via FORWARD_GEOCODING_PROVIDER env var ("photon" or "nominatim").
    Note: setting "nominatim" here will raise NotImplementedError on search()
    because NominatimProvider.search() is not for production autocomplete.
    """
    provider_name = config.FORWARD_GEOCODING_PROVIDER.lower()
    if provider_name == "photon":
        return _photon_singleton()
    if provider_name == "nominatim":
        # Allowed for testing only; callers must be aware of usage restrictions.
        return _nominatim_singleton()
    raise ValueError(
        f"Unknown FORWARD_GEOCODING_PROVIDER: {provider_name!r}. "
        "Valid values: 'photon', 'nominatim'."
    )


def get_reverse_geocoding_provider() -> NominatimProvider:
    """
    Return the reverse-geocoding provider.

    Always returns NominatimProvider regardless of FORWARD_GEOCODING_PROVIDER.
    Reverse geocoding must NEVER use Photon (not designed for it) and must
    NEVER be called in autocomplete/typeahead context.
    """
    return _nominatim_singleton()


# ---------------------------------------------------------------------------
# Backward-compatibility alias
# ---------------------------------------------------------------------------
# endpoints.py still calls get_geocoding_provider() for forward search.
# This alias will be replaced in Stage C when endpoints.py is updated.

def get_geocoding_provider() -> GeocodingProvider:
    """
    Backward-compatible alias for get_forward_geocoding_provider().
    Deprecated: Stage C will update callers to use the explicit factories.
    """
    return get_forward_geocoding_provider()
