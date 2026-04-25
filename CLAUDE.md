# CommonArtist — Dev Rules

## What this is
Open source co-op gallery management platform. FastAPI + PostgreSQL + Jinja2. Self-hostable via Docker Compose.

## Stack
- FastAPI (async), SQLAlchemy 2.x ORM, PostgreSQL
- Jinja2 templates, Alpine.js for interactivity
- structlog for all logging (JSON, structured)
- Docker Compose for local dev and deployment

## Architecture
```
app/
  main.py          FastAPI app factory, router registration, lifespan
  database.py      Async engine, Base, get_db()
  monitor/         structlog config, alert rules engine
  routers/         health, admin, portal, artists, payouts, sync
  models/          SQLAlchemy ORM models
  adapters/        POS adapters (shopify, square, manual)
docs/plans/        PRD and planning docs
```

## Monitor-first rule
Every feature that can fail must ship with a named monitor hook. If you add a feature, ask: what breaks here? Add a structured log event and/or alert rule for it. See `app/monitor/`.

## No non-ASCII characters in Python files
FastAPI runs on Python 3.12 — non-ASCII chars (em dashes, curly quotes) in .py files crash the tokenizer.

## Logging
Always use `from app.monitor import logger` and structured events:
```python
logger.info("commonartist.module.action", key=value)
logger.error("commonartist.module.action", error=str(e))
```
Event names follow `commonartist.<module>.<action>` convention.

## Environment
All config via environment variables. Never hardcode secrets. See `.env.example`.

## Testing
Tests live in `tests/`. Use pytest + httpx AsyncClient for route tests.
