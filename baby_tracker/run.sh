#!/bin/bash
set -e

log_info() {
    echo "[INFO] $(date +%H:%M:%S): $1"
}

log_info "Starting Baby Tracker addon..."

mkdir -p /data/db

export DATA_DIR="/data"
export DATABASE_URL="sqlite:////data/db/baby_tracker.db"

OPTS=/data/options.json

export LANGUAGE=$(python3 -c "import json,sys; d=json.load(open('$OPTS')); print(d.get('language','nl'))" 2>/dev/null || echo "nl")
export BABY_NAME=$(python3 -c "import json,sys; d=json.load(open('$OPTS')); print(d.get('baby_name',''))" 2>/dev/null || echo "")
export BABY_BIRTH_DATE=$(python3 -c "import json,sys; d=json.load(open('$OPTS')); print(d.get('baby_birth_date',''))" 2>/dev/null || echo "")

log_info "Language: $LANGUAGE"
log_info "Baby: $BABY_NAME"
log_info "Starting server on port 8765..."

exec uvicorn app.main:app --host 0.0.0.0 --port 8765 --workers 1
