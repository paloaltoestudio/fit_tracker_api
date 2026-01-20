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
