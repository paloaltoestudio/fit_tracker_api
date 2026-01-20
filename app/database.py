from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get database URL from environment (Render provides DATABASE_URL)
# For SQLite (local dev), use the default
database_url = os.getenv("DATABASE_URL", "sqlite:///./fit_tracker.db")

# Render's PostgreSQL URLs use postgres:// but SQLAlchemy needs postgresql://
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

# Configure engine based on database type
if database_url.startswith("sqlite"):
    engine = create_engine(
        database_url, connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL (for production on Render)
    engine = create_engine(database_url)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
