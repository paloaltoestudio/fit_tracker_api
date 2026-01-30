from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import User, Weight, MetricEntry  # Import models so tables are created
from app.routers import auth, weights, profile, metrics

# Create database tables (must import models first)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fit Tracker API", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api/v1", tags=["authentication"])
app.include_router(weights.router, prefix="/api/v1", tags=["weights"])
app.include_router(profile.router, prefix="/api/v1", tags=["profile"])
app.include_router(metrics.router, prefix="/api/v1", tags=["metrics"])


@app.get("/")
async def root():
    return {"message": "Fit Tracker API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
