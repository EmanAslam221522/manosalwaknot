#!/bin/sh
set -eu

attempt=1
max_attempts=5

until alembic upgrade head; do
  if [ "$attempt" -ge "$max_attempts" ]; then
    echo "Database migration failed after ${attempt} attempts." >&2
    exit 1
  fi

  delay=$((attempt * 3))
  echo "Migration attempt ${attempt} failed; retrying in ${delay}s." >&2
  sleep "$delay"
  attempt=$((attempt + 1))
done

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
