#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database and running Alembic migrations..."
ATTEMPTS=0
until alembic upgrade head; do
  ATTEMPTS=$((ATTEMPTS+1))
  if [ "$ATTEMPTS" -ge 30 ]; then
    echo "Alembic failed after $ATTEMPTS attempts. Exiting."
    exit 1
  fi
  echo "Alembic failed, retrying in 2s... ($ATTEMPTS)"
  sleep 2
done

echo "Starting Gunicorn..."
exec gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000 app.main:app
