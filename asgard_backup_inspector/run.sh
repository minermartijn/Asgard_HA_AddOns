#!/bin/sh
set -eu

# Options are read by the Python app from /data/options.json.
# Never print the Supervisor token or backup names here.
echo "[INFO] Starting ASGARD Backup Inspector on internal Ingress port 8099"

exec uvicorn app.main:create_app --factory \
    --host 0.0.0.0 --port 8099 --workers 1 \
    --no-server-header --no-access-log
