"""
Geocoding service with provider abstraction.

External geocoders are used ONLY for place/address discovery.
They must NEVER be used to infer transport routes or connections.
All results carry explicit provenance labels.
"""

import abc
import time
import urllib.parse
import urllib.request
import json
import logging
from typing import List, Optional, Dict, Any, Tuple

from app.core import config

logger = logging.getLogger(__name__)

# Attribution string required by Nominatim / OSM usage policy
OSM_ATTRIBUTION = "Places/addresses: © OpenStreetMap contributors (ODbL)"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class GeocodedPlace:
    """Represents a geocoded place/address result from an external provider."""

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
    """Abstract geocoding provider.  Implementations must be thread-safe."""

    @abc.abstractmethod
    def search(self, query: str, limit: int = 5) -> List[GeocodedPlace]:
        """Search for places matching *query*.  Returns Chennai-filtered results."""

    @abc.abstractmethod
    def reverse(self, lat: float, lng: float) -> Optional[GeocodedPlace]:
        """Reverse-geocode a coordinate to a place."""


# ---------------------------------------------------------------------------
# Nominatim implementation
# ---------------------------------------------------------------------------

class NominatimProvider(GeocodingProvider):
    """
    Nominatim (OpenStreetMap) geocoding provider.

    Usage policy compliance:
    - Maximum 1 request per second (enforced via _last_request_time).
    - User-Agent header identifying this application.
    - In-memory TTL cache (default 5 min) to avoid repeated identical queries.
    - Results bounded to Chennai bounding box.
    - Attribution: © OpenStreetMap contributors.
    """

    def __init__(self):
        self._base_url = config.NOMINATIM_BASE_URL.rstrip("/")
        self._user_agent = config.NOMINATIM_USER_AGENT
        self._cache_ttl = config.NOMINATIM_CACHE_TTL
        # cache: key -> (timestamp, value)
        self._search_cache: Dict[Tuple, Tuple[float, List[GeocodedPlace]]] = {}
        self._reverse_cache: Dict[Tuple, Tuple[float, Optional[GeocodedPlace]]] = {}
        self._last_request_time: float = 0.0

    # ------------------------------------------------------------------
    # Rate limiting
    # ------------------------------------------------------------------

    def _rate_limit(self):
        """Ensure at least 1 second between requests (Nominatim usage policy)."""
        elapsed = time.monotonic() - self._last_request_time
        wait = 1.0 - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_time = time.monotonic()

    # ------------------------------------------------------------------
    # HTTP helper
    # ------------------------------------------------------------------

    def _get_json(self, url: str) -> Any:
        """Perform a GET request and return parsed JSON, or None on error."""
        self._rate_limit()
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self._user_agent,
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            logger.warning("Nominatim request failed for %s: %s", url, exc)
            return None

    # ------------------------------------------------------------------
    # Chennai bbox filter
    # ------------------------------------------------------------------

    @staticmethod
    def _in_chennai(lat: float, lng: float) -> bool:
        bb = config.CHENNAI_BBOX
        return (
            bb["min_lat"] <= lat <= bb["max_lat"]
            and bb["min_lng"] <= lng <= bb["max_lng"]
        )

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    def _search_cache_get(self, key: Tuple) -> Optional[List[GeocodedPlace]]:
        entry = self._search_cache.get(key)
        if entry and (time.monotonic() - entry[0]) < self._cache_ttl:
            return entry[1]
        return None

    def _search_cache_set(self, key: Tuple, value: List[GeocodedPlace]):
        self._search_cache[key] = (time.monotonic(), value)

    def _reverse_cache_get(self, key: Tuple) -> Optional[Optional[GeocodedPlace]]:
        entry = self._reverse_cache.get(key)
        if entry and (time.monotonic() - entry[0]) < self._cache_ttl:
            return entry[1]  # may be None (cached "no result")
        return _SENTINEL

    def _reverse_cache_set(self, key: Tuple, value: Optional[GeocodedPlace]):
        self._reverse_cache[key] = (time.monotonic(), value)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def search(self, query: str, limit: int = 5) -> List[GeocodedPlace]:
        query = query.strip()
        if not query:
            return []
        key = (query.lower(), limit)
        cached = self._search_cache_get(key)
        if cached is not None:
            return cached

        # Append "Chennai" if not already present to bias results
        nominatim_query = query if "chennai" in query.lower() else f"{query}, Chennai"
        params = urllib.parse.urlencode(
            {
                "q": nominatim_query,
                "format": "jsonv2",
                "limit": min(limit * 2, 20),  # fetch extras to allow bbox filter
                "bounded": "1",
                "viewbox": config.NOMINATIM_VIEWBOX,
                "countrycodes": "in",
                "addressdetails": "1",
            }
        )
        url = f"{self._base_url}/search?{params}"
        raw = self._get_json(url)

        results: List[GeocodedPlace] = []
        if raw and isinstance(raw, list):
            for item in raw:
                try:
                    lat = float(item["lat"])
                    lng = float(item["lon"])
                    if not self._in_chennai(lat, lng):
                        continue
                    osm_id = str(item.get("osm_id", ""))
                    osm_type = item.get("osm_type", "n")
                    display = item.get("display_name", "")
                    # Short name: first part of display_name
                    short_name = display.split(",")[0].strip() if display else query
                    results.append(
                        GeocodedPlace(
                            id=f"nom_{osm_type}{osm_id}",
                            name=short_name,
                            display_address=display,
                            lat=lat,
                            lng=lng,
                            category="place",
                            source="nominatim_osm",
                            provenance="Nominatim/OSM (external geocoder) — NOT a transport network source",
                            is_verified=False,
                        )
                    )
                except (KeyError, ValueError, TypeError):
                    continue
                if len(results) >= limit:
                    break

        self._search_cache_set(key, results)
        return results

    def reverse(self, lat: float, lng: float) -> Optional[GeocodedPlace]:
        if not self._in_chennai(lat, lng):
            return None
        key = (round(lat, 5), round(lng, 5))
        cached = self._reverse_cache_get(key)
        if cached is not _SENTINEL:
            return cached

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
                    id=f"nom_rev_{round(lat,5)}_{round(lng,5)}",
                    name=short_name,
                    display_address=display,
                    lat=rlat,
                    lng=rlng,
                    category="place",
                    source="nominatim_osm",
                    provenance="Nominatim/OSM reverse geocode (external) — NOT a transport network source",
                    is_verified=False,
                )
            except (KeyError, ValueError, TypeError):
                result = None

        self._reverse_cache_set(key, result)
        return result


# Sentinel distinguishing "not cached" from "cached None"
_SENTINEL = object()


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_geocoding_provider() -> GeocodingProvider:
    """Return the configured geocoding provider (singleton pattern per process)."""
    provider = config.GEOCODING_PROVIDER.lower()
    if provider == "nominatim":
        return _nominatim_singleton()
    raise ValueError(f"Unknown GEOCODING_PROVIDER: {provider!r}")


_nominatim_instance: Optional[NominatimProvider] = None


def _nominatim_singleton() -> NominatimProvider:
    global _nominatim_instance
    if _nominatim_instance is None:
        _nominatim_instance = NominatimProvider()
    return _nominatim_instance
