from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from app.models.schemas import (
    HealthResponse,
    Place,
    SearchRequest,
    SearchResponse,
)
from app.services.data_loader import TransitDataLoader
from app.services.routing_engine import MultimodalRoutingEngine

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def get_health():
    loader = TransitDataLoader.get_instance()
    is_loaded = len(loader.places_index) > 0
    return HealthResponse(status="ok", version="1.0.0", data_loaded=is_loaded)

@router.get("/places", response_model=List[Place])
def get_places(
    q: Optional[str] = Query(None, description="Search query for Chennai places or stops"),
    limit: int = Query(10, ge=1, le=50, description="Max results to return")
):
    loader = TransitDataLoader.get_instance()
    results = loader.search_places(query=q or "", limit=limit)
    return [
        Place(
            id=p["id"],
            name=p["name"],
            category=p["category"],
            lat=p["lat"],
            lng=p["lng"],
            source=p.get("source", "theme7"),
            description=p.get("description"),
        )
        for p in results
    ]

@router.post("/routes/search", response_model=SearchResponse)
def search_routes(request: SearchRequest):
    if not (-90 <= request.origin.lat <= 90 and -180 <= request.origin.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid origin coordinates")
    if not (-90 <= request.destination.lat <= 90 and -180 <= request.destination.lng <= 180):
        raise HTTPException(status_code=400, detail="Invalid destination coordinates")

    loader = TransitDataLoader.get_instance()
    engine = MultimodalRoutingEngine(data_loader=loader)
    return engine.search_routes(request)
