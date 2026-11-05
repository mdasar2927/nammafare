from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class TransportMode(str, Enum):
    WALKING = "walking"
    BUS = "bus"
    METRO = "metro"
    SUBURBAN_TRAIN = "suburban_train"
    AUTO = "auto"
    SHARE_AUTO = "share_auto"
    TAXI = "taxi"

class BusType(str, Enum):
    ORDINARY = "ordinary"
    EXPRESS = "express"
    DELUXE = "deluxe"
    AC = "ac"

class SortPreference(str, Enum):
    CHEAPEST = "cheapest"
    FASTEST = "fastest"

class Coordinates(BaseModel):
    lat: float
    lng: float
    name: Optional[str] = None

class Place(BaseModel):
    id: str
    name: str
    category: str  # "bus_stop", "metro_station", "railway_station"
    lat: float
    lng: float
    source: str = "theme7"
    description: Optional[str] = None

class RouteLeg(BaseModel):
    mode: str
    route_number: Optional[str] = None
    bus_type: Optional[str] = None
    from_name: str
    to_name: str
    duration_minutes: int
    distance_meters: int
    fare: float
    fare_note: Optional[str] = None
    is_estimated: bool = False
    is_verified: bool = False
    provenance: Optional[str] = None
    polyline: Optional[List[List[float]]] = None

class RouteOption(BaseModel):
    route_id: str
    summary: str
    total_fare: float
    total_duration_minutes: int
    total_distance_meters: int
    transfers_count: int
    departure_time: str
    arrival_time: str
    is_cheapest: bool = False
    is_fastest: bool = False
    is_verified: bool = False
    provenance: Optional[str] = None
    legs: List[RouteLeg]

class SearchRequest(BaseModel):
    origin: Coordinates
    destination: Coordinates
    gender: Optional[str] = "other"
    allowed_modes: Optional[List[str]] = Field(
        default_factory=lambda: [
            "walking",
            "bus",
            "metro",
            "suburban_train",
        ]
    )
    departure_time: Optional[str] = None
    sort_by: Optional[str] = "cheapest"

class SearchResponse(BaseModel):
    search_id: str
    origin: str
    destination: str
    departure_time: str
    gender: str
    origin_taz: Optional[str] = None
    destination_taz: Optional[str] = None
    message: Optional[str] = None
    routes: List[RouteOption]

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    data_loaded: bool = True
    theme7_bus_stops_count: int = 0
    theme7_bus_routes_count: int = 0
    theme7_metro_corridors_count: int = 0
    theme7_metro_stations_count: int = 0
    theme7_suburban_tracks_count: int = 0
    theme7_suburban_stations_count: int = 0
    theme7_taz_zones_count: int = 0
    theme7_road_links_count: int = 0
