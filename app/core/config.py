"""Application configuration — values loaded from environment variables with safe defaults."""
import os

# ---------------------------------------------------------------------------
# Autocomplete / forward-geocoding provider
# ---------------------------------------------------------------------------
# "photon"    — Photon (OSM-based, autocomplete-safe). Default.
# "nominatim" — Nominatim (OSM). NOT autocomplete-safe; retained only for
#               reverse geocoding and testing. Do not set this for production
#               autocomplete use — Nominatim's usage policy forbids typeahead.
FORWARD_GEOCODING_PROVIDER: str = os.getenv("FORWARD_GEOCODING_PROVIDER", "photon")

# ---------------------------------------------------------------------------
# Photon settings (forward geocoding / autocomplete)
# ---------------------------------------------------------------------------
# Public Photon demo: https://photon.komoot.io  (no API key, rate-limited)
# Self-hosted:        set PHOTON_BASE_URL to your own instance URL.
PHOTON_BASE_URL: str = os.getenv("PHOTON_BASE_URL", "https://photon.komoot.io")

# Request timeout in seconds for Photon calls
PHOTON_TIMEOUT: int = int(os.getenv("PHOTON_TIMEOUT", "5"))

# In-memory TTL cache duration in seconds (default 5 minutes).
# Caching is mandatory to stay within reasonable usage of the public demo API.
PHOTON_CACHE_TTL: int = int(os.getenv("PHOTON_CACHE_TTL", "300"))

# Max results requested from Photon per autocomplete call
PHOTON_MAX_RESULTS: int = int(os.getenv("PHOTON_MAX_RESULTS", "10"))

# ---------------------------------------------------------------------------
# Nominatim settings (reverse geocoding ONLY)
# ---------------------------------------------------------------------------
# Nominatim usage policy: https://operations.osmfoundation.org/policies/nominatim/
#   - Identifying User-Agent header required.
#   - 1 request per second maximum.
#   - Autocomplete/typeahead is explicitly PROHIBITED.
#   - Nominatim is therefore used ONLY for /places/reverse.
NOMINATIM_BASE_URL: str = os.getenv(
    "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org"
)
NOMINATIM_USER_AGENT: str = os.getenv(
    "NOMINATIM_USER_AGENT",
    "NammaFare-Chennai-Transit-Planner/1.0 (contact@nammafare.in)",
)
# Request timeout in seconds for Nominatim calls
NOMINATIM_TIMEOUT: int = int(os.getenv("NOMINATIM_TIMEOUT", "8"))
# In-memory reverse-geocode cache TTL in seconds (default 10 minutes)
NOMINATIM_CACHE_TTL: int = int(os.getenv("NOMINATIM_CACHE_TTL", "600"))

# ---------------------------------------------------------------------------
# Chennai bounding box — applied to ALL external geocoder results
# ---------------------------------------------------------------------------
# Generous bbox covering the full Chennai Metropolitan Region.
# Results outside this box are silently discarded.
CHENNAI_BBOX: dict = {
    "min_lat": 12.5,
    "max_lat": 13.5,
    "min_lng": 79.8,
    "max_lng": 80.5,
}

# Photon bbox filter string: lon_min,lat_min,lon_max,lat_max
PHOTON_BBOX: str = (
    f"{CHENNAI_BBOX['min_lng']},{CHENNAI_BBOX['min_lat']},"
    f"{CHENNAI_BBOX['max_lng']},{CHENNAI_BBOX['max_lat']}"
)

# Nominatim viewbox string (same bbox, same format)
NOMINATIM_VIEWBOX: str = PHOTON_BBOX

# ---------------------------------------------------------------------------
# General geocoding limits
# ---------------------------------------------------------------------------
# Max external geocoder results merged into /api/v1/places (flat list endpoint)
GEOCODER_MAX_RESULTS: int = int(os.getenv("GEOCODER_MAX_RESULTS", "5"))

# ---------------------------------------------------------------------------
# Nearby transport search defaults
# ---------------------------------------------------------------------------
NEARBY_DEFAULT_RADIUS_M: int = int(os.getenv("NEARBY_DEFAULT_RADIUS_M", "800"))
NEARBY_MAX_BUS_STOPS: int = 10
NEARBY_MAX_METRO: int = 5
NEARBY_MAX_RAIL: int = 5
