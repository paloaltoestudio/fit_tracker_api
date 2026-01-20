from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import User  # Import models so tables are created
from app.routers import auth

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


@app.get("/")
async def root():
    return {"message": "Fit Tracker API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
