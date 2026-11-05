from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.endpoints import router as api_v1_router
from app.services.data_loader import TransitDataLoader

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Preloading complete Theme7 transport dataset into memory...")
    loader = TransitDataLoader.get_instance()
    print(
        f"Theme7 Loaded: {len(loader.bus_stops)} bus stops, "
        f"{len(loader.bus_routes)} bus routes, "
        f"{len(loader.metro_corridors)} metro corridors, "
        f"{len(loader.metro_stations)} metro stations, "
        f"{len(loader.suburban_tracks)} suburban tracks, "
        f"{len(loader.suburban_stations)} suburban stations, "
        f"{len(loader.road_network)} road links, "
        f"{len(loader.taz_zones)} TAZ zones."
    )
    yield

app = FastAPI(
    title="NammaFare Pure Data-Driven Transit Engine",
    description="Chennai Multimodal Journey Planner derived strictly from Theme7 Public Transport Datasets",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include v1 API routes
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/")
def root():
    return {
        "message": "NammaFare Pure Data-Driven Transit Engine is active.",
        "docs_url": "/docs",
        "api_v1_prefix": "/api/v1",
        "data_policy": "STRICT - 100% Theme7 Derived Data Only"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
