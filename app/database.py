from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Get database URL from environment variable (set to Neon PostgreSQL URL in production)
# For SQLite (local dev), use the default
database_url = os.getenv("DATABASE_URL", "sqlite:///./fit_tracker.db")

# Neon PostgreSQL URLs use postgresql:// but SQLAlchemy needs the psycopg driver specified
# Also handles legacy postgres:// URLs
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
elif database_url.startswith("postgresql://") and "+" not in database_url:
    # If it's postgresql:// without a driver, add psycopg driver
    database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)

# Configure engine based on database type
if database_url.startswith("sqlite"):
    engine = create_engine(
        database_url, connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL (Neon in production, deployed on Render)
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
