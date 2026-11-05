"""Application configuration — values loaded from environment variables with safe defaults."""
import os

# --- Geocoding provider ---
GEOCODING_PROVIDER: str = os.getenv("GEOCODING_PROVIDER", "nominatim")

# Nominatim (OpenStreetMap) settings
NOMINATIM_BASE_URL: str = os.getenv(
    "NOMINATIM_BASE_URL", "https://nominatim.openstreetmap.org"
)
NOMINATIM_USER_AGENT: str = os.getenv(
    "NOMINATIM_USER_AGENT",
    "NammaFare-Chennai-Transit-Planner/1.0 (contact@nammafare.in)",
)
# Nominatim cache TTL in seconds (default 5 minutes)
NOMINATIM_CACHE_TTL: int = int(os.getenv("NOMINATIM_CACHE_TTL", "300"))

# --- Chennai bounding box (used to filter geocoder results) ---
# Generous bbox covering the full Chennai Metropolitan Region
CHENNAI_BBOX: dict = {
    "min_lat": 12.5,
    "max_lat": 13.5,
    "min_lng": 79.8,
    "max_lng": 80.5,
}
# viewbox parameter string for Nominatim (lon1,lat1,lon2,lat2)
NOMINATIM_VIEWBOX: str = (
    f"{CHENNAI_BBOX['min_lng']},{CHENNAI_BBOX['min_lat']},"
    f"{CHENNAI_BBOX['max_lng']},{CHENNAI_BBOX['max_lat']}"
)

# Max results per category from geocoder
GEOCODER_MAX_RESULTS: int = int(os.getenv("GEOCODER_MAX_RESULTS", "5"))

# Nearby transport search defaults
NEARBY_DEFAULT_RADIUS_M: int = int(os.getenv("NEARBY_DEFAULT_RADIUS_M", "800"))
NEARBY_MAX_BUS_STOPS: int = 10
NEARBY_MAX_METRO: int = 5
NEARBY_MAX_RAIL: int = 5
