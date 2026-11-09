#!/bin/sh
set -eu

# Render/Koyeb inject PORT. Local Docker falls back to 8000.
alembic upgrade head
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
