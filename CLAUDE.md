# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Activate virtual environment
source env/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload

# Database migrations
alembic upgrade head                                    # Apply all pending migrations
alembic revision --autogenerate -m "Describe change"   # Create migration after editing models.py
alembic current                                         # Show current revision
alembic downgrade -1                                    # Roll back one revision
alembic stamp 001_initial                               # Mark DB at initial revision (for existing DBs)
```

## Architecture

This is a FastAPI REST API for fitness tracking, deployed on Render with PostgreSQL in production and SQLite locally.

**Entry point:** `main.py` — creates FastAPI app, registers CORS middleware, mounts all routers under `/api/v1`, and calls `Base.metadata.create_all()` to initialize tables on startup.

**Key modules:**
- `app/models.py` — SQLAlchemy ORM models (`User`, `Weight`, `MetricEntry`). After any model change, generate and apply a migration.
- `app/schemas.py` — Pydantic v2 request/response schemas and metric value validation logic.
- `app/auth.py` — JWT creation/verification (HS256) and bcrypt password hashing. Token payload contains `sub` (username) and `user_id`.
- `app/database.py` — Engine setup; auto-converts `postgres://` URLs to `postgresql+psycopg://` for psycopg v3 compatibility.
- `app/config.py` — Settings via `pydantic-settings`; reads from `.env` or environment variables (`DATABASE_URL`, `SECRET_KEY`).

**Routers** (`app/routers/`):
- `auth.py` — `POST /login`, `POST /register`
- `weights.py` — CRUD for weight entries; one entry per user per date enforced at app level
- `profile.py` — `GET`/`PUT` profile fields on the `User` model
- `metrics.py` — CRUD for `MetricEntry`; supports `metric_type` values `"weight"` and `"muscle_index"` with a unique constraint on `(user_id, metric_type, date)`

**Auth pattern:** Protected routes use `HTTPBearer` + a local `get_current_user()` dependency defined in each router file (not a shared dependency), which calls `get_current_user_id()` from `app/auth.py`.

**Database:** SQLite for local dev (`fit_tracker.db`), Neon PostgreSQL in production (app deployed on Render). Migrations are managed by Alembic — run against Neon from your laptop by setting `DATABASE_URL` to the Neon connection string before running `alembic upgrade head`. Update `DATABASE_URL` in Render's environment variables to point to Neon.
