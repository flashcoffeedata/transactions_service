# Order Status API

Production-oriented REST API for atomic order-status ingestion and filtered retrieval. It uses FastAPI, async SQLAlchemy, PostgreSQL, Alembic, Pydantic, and API-key authentication.

## Run with Docker

1. Create the environment file and replace both secrets:

   ```bash
   cp .env.example .env
   # Set POSTGRES_PASSWORD and API_KEY in .env
   ```

   Add `POSTGRES_PASSWORD` to `.env`; `API_KEY` must be at least 16 characters.

2. Start PostgreSQL, run the migration, and start the API:

   ```bash
   docker compose up --build
   ```

3. Open Swagger UI at <http://localhost:8000/docs>. The unauthenticated health check is at <http://localhost:8000/health>.

## Run locally

Python 3.11+ and PostgreSQL are required.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit DATABASE_URL and API_KEY
alembic upgrade head
uvicorn app.main:app --reload
```

Use an async URL for the app, for example `postgresql+asyncpg://user:password@localhost:5432/order_status`. Alembic automatically uses the synchronous psycopg driver.

## API examples

Create or atomically update an order (the original `created_at` is preserved):

```bash
curl -X POST http://localhost:8000/api/orders \
  -H 'Content-Type: application/json' \
  -H 'X-API-Key: replace-with-a-long-random-secret' \
  -d '{"order_id":"109ed62b-2129-4913-998d-162fc8df6dfe","status":"completed"}'
```

Retrieve orders:

```bash
curl 'http://localhost:8000/api/orders?start_date=2026-10-01&end_date=2026-10-28&status=completed&page=1&limit=100' \
  -H 'X-API-Key: replace-with-a-long-random-secret'
```

Dates are interpreted as complete UTC calendar dates: `start_date` is inclusive at 00:00:00Z and `end_date` is implemented as an exclusive bound at 00:00:00Z on the following day.

## Configuration

| Variable | Purpose | Default |
|---|---|---|
| `DATABASE_URL` | Async SQLAlchemy PostgreSQL URL | required |
| `API_KEY` | Secret accepted in `X-API-Key` (16+ chars) | required |
| `ENVIRONMENT` | Environment label used in logs | `development` |
| `LOG_LEVEL` | Application log level | `INFO` |
| `MAX_PAGE_LIMIT` | Maximum allowed retrieval limit | `500` |
| `DB_POOL_SIZE` | Persistent connection count | `10` |
| `DB_MAX_OVERFLOW` | Additional burst connections | `20` |

Do not commit `.env`. Rotate exposed API keys and database credentials immediately.

## Tests

The automated suite uses in-memory SQLite for fast, isolated HTTP-level tests. Production uses PostgreSQL's `INSERT ... ON CONFLICT DO UPDATE`; SQLite's equivalent is exercised in tests.

```bash
pytest -q
```

Tests cover insert/update behavior, UUID and payload validation, authentication, filters, pagination, invalid date ranges, and concurrent upserts.

## Operations

- Apply migrations before starting a new application version: `alembic upgrade head`.
- Roll back one migration when appropriate: `alembic downgrade -1`.
- `/health` returns HTTP 503 if a database connection cannot be established.
- Logs avoid request bodies, API keys, and database credentials.
- The container runs as an unprivileged user and Compose includes database and API health checks plus restart policies.
