#!/usr/bin/env bash
set -euo pipefail

echo "Waiting for database and running Alembic migrations..."

# Pre-wait for Postgres TCP to accept connections to avoid noisy tracebacks
PGHOST="${POSTGRES_HOST:-postgres}"
PGPORT="${POSTGRES_PORT:-5432}"
echo "Checking Postgres TCP at ${PGHOST}:${PGPORT} ..."
for i in $(seq 1 60); do
  if bash -lc ":> /dev/tcp/${PGHOST}/${PGPORT}" 2>/dev/null; then
    echo "Postgres is reachable."
    break
  fi
  echo "[$i/60] Waiting for Postgres ..."
  sleep 1
done
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
# Seed default superadmin if configured (dev convenience)
python - <<'PY'
try:
    from app.bootstrap import create_default_superadmin, repair_sequences
    # Align sequences with existing rows to prevent PK collisions
    repair_sequences()
    create_default_superadmin()
    print("[bootstrap] default superadmin check complete")
except Exception as e:
    print("[bootstrap] skipped or failed:", e)
PY
exec gunicorn -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:8000 app.main:app
