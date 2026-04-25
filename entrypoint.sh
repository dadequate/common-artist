#!/bin/sh
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Starting CommonArtist..."
if [ "${RELOAD:-0}" = "1" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
else
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000
fi
