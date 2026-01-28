# Fit Tracker API

A FastAPI-based fitness tracking application.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the application:
```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once the server is running, you can access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Endpoints

### Authentication

- `POST /api/v1/login` - Login and get JWT token
  - Request body: `{"username": "string", "password": "string"}`
  - Returns: `{"access_token": "string", "token_type": "bearer"}`

- `POST /api/v1/register` - Register a new user (for development)
  - Request body: `{"username": "string", "password": "string"}`
  - Returns: User information

## Database

The application uses SQLite for development. The database file `fit_tracker.db` will be created automatically on first run.

### Migrations (Alembic)

Migrations add or change columns without dropping data.

**If you already have a database** (e.g. created by the app before profile was added):

1. Mark the DB as being at the initial revision:
   ```bash
   alembic stamp 001_initial
   ```
2. Apply new migrations (adds profile columns, etc.):
   ```bash
   alembic upgrade head
   ```

**If you're starting with an empty or new database:**

```bash
alembic upgrade head
```

**Other commands:**

- `alembic current` — show current revision
- `alembic history` — list revisions
- `alembic downgrade -1` — roll back one revision
- `alembic upgrade head` — apply all pending migrations

**After changing `app/models.py`**, create a new migration:

```bash
alembic revision --autogenerate -m "Describe your change"
alembic upgrade head
```

### Running migrations on Render (PostgreSQL)

Deploying new code does **not** run migrations by itself. Render’s Postgres only changes when *you* run Alembic (or when a Pre-Deploy command runs it, if you have that).

**Environment:** Your Postgres must be linked to the service so `DATABASE_URL` is set. Get that URL from **Dashboard → PostgreSQL → Info** (Internal Database URL) or from your Web Service **Environment**.

---

#### Free tier (no Shell, no Pre-Deploy)

On the free tier you run **all** migrations from your laptop, with `DATABASE_URL` set to Render’s Postgres URL. You never run anything on Render itself.

**One-time: existing DB** (tables were created by the app with `create_all`, no profile columns yet):

```bash
export DATABASE_URL="postgres://user:pass@host/dbname"   # your real Render URL
alembic stamp 001_initial
alembic upgrade head
```

Then deploy. After that, Render’s DB is in sync with your migrations.

**Every new migration after that:**

1. Edit `app/models.py`.
2. Locally (SQLite): `alembic revision --autogenerate -m "Add xyz"` then `alembic upgrade head`.
3. Commit the new file in `alembic/versions/` and push.
4. **Before (or right after) deploy**, run against Render’s DB from your laptop:
   ```bash
   export DATABASE_URL="postgres://user:pass@host/dbname"
   alembic upgrade head
   ```
5. Deploy.

So for each new migration you do two things: `alembic upgrade head` on local SQLite (step 2), and again with `DATABASE_URL` set to Render’s URL (step 4). The second run is what updates Render’s Postgres; without Pre-Deploy, nothing on Render runs it for you.

---

#### If you have Pre-Deploy (paid / higher tiers)

1. In Render: **Settings → Build & Deploy → Pre-Deploy Command** → `alembic upgrade head`.
2. One-time for an existing DB: run `alembic stamp 001_initial` and `alembic upgrade head` from your laptop with Render’s `DATABASE_URL` (same as above).
3. From then on: create migrations locally, commit, push, deploy. Pre-Deploy runs `alembic upgrade head` on Render; you don’t run it against Render’s DB from your machine.
