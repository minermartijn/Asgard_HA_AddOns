#!/bin/sh
set -e

echo "[INFO] Starting ASGARD RainBreak on internal Ingress port 8097"

exec python3 -u -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8097 \
    --log-level info \
    --access-log
