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

Deploying new code does **not** run migrations by itself. You need Render to run `alembic upgrade head` before each deploy.

1. **Pre-Deploy Command (recommended)**  
   In the Render dashboard: your Web Service → **Settings** → **Build & Deploy** → **Pre-Deploy Command**  
   Set it to:
   ```bash
   alembic upgrade head
   ```
   Render runs this before switching traffic to the new version. If it fails, the deploy is aborted and the previous version stays live.

2. **Environment**  
   Your Postgres database must be linked to the service so `DATABASE_URL` is set (Render does this when you add the DB). Alembic uses that same variable.

3. **First deploy / “stamp” without Shell (Free tier)**  
   On the free tier there is no Shell. Run migrations from your **local machine** using Render’s Postgres URL:

   - **New Postgres DB (no tables yet):**  
     Deploy as usual. Pre-Deploy runs `alembic upgrade head` and creates all tables. Nothing else to do.

   - **Existing Postgres DB** (tables were created by the app with `create_all`, e.g. before profile columns existed):  
     1. In Render: **Dashboard** → your **PostgreSQL** → **Info** (or your **Web Service** → **Environment**). Copy the **Internal Database URL** (or the `DATABASE_URL` your service uses).  
     2. On your laptop, open a **terminal**, `cd` into the project root, and run the commands below. **Where to set `DATABASE_URL`:** only in that terminal session—either **inline** (left side of the command) or with **`export`** first; you do **not** add it to a config file.

        **Option A – inline (one command at a time):**
        ```bash
        DATABASE_URL="postgres://user:pass@host/dbname" alembic stamp 001_initial
        DATABASE_URL="postgres://user:pass@host/dbname" alembic upgrade head
        ```
        Replace `postgres://user:pass@host/dbname` with your real URL from Render.

        **Option B – export in the same terminal, then run Alembic:**
        ```bash
        export DATABASE_URL="postgres://user:pass@host/dbname"
        alembic stamp 001_initial
        alembic upgrade head
        ```
        Again, use your real URL. The variable applies only to that terminal window until you close it.

     3. Deploy. Pre-Deploy will run `alembic upgrade head` on future deploys; your DB is already up to date.

   That way you never need Render’s Shell.

After that, each deploy runs the Pre-Deploy Command and applies any new migrations automatically.
