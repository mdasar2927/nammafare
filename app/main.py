from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.v1.endpoints import router as api_v1_router
from app.services.data_loader import TransitDataLoader

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload Theme7 dataset into memory on startup
    print("Preloading Theme7 transport dataset...")
    loader = TransitDataLoader.get_instance()
    print(f"Loaded {len(loader.bus_stops)} bus stops, {len(loader.bus_routes)} bus routes, and {len(loader.places_index)} indexed places.")
    yield

app = FastAPI(
    title="NammaFare Backend API",
    description="Multimodal Chennai Journey Planner & Fare Transparency Engine",
    version="1.0.0",
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
        "message": "NammaFare Chennai Multimodal API is running.",
        "docs_url": "/docs",
        "api_v1_prefix": "/api/v1"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
