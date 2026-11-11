#!/bin/sh
set -e

echo "[INFO] Starting ASGARD NotifyHub on internal Ingress port 8098"

exec python3 -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8098 \
    --log-level info
