#!/bin/bash
set -e

log_info() {
    echo "[INFO] $(date +%H:%M:%S): $1"
}

log_info "Starting Home Stock addon..."

mkdir -p /data/db

export DATA_DIR="/data"
export DATABASE_URL="sqlite:////data/db/home_stock.db"

OPTS=/data/options.json

# Read add-on options from /data/options.json (inline python, with safe fallbacks)
export LANGUAGE=$(python3 -c "import json; d=json.load(open('$OPTS')); print(d.get('language','nl'))" 2>/dev/null || echo "nl")
export HOUSEHOLD_NAME=$(python3 -c "import json; d=json.load(open('$OPTS')); print(d.get('household_name',''))" 2>/dev/null || echo "")
export TODO_ENTITY=$(python3 -c "import json; d=json.load(open('$OPTS')); print(d.get('todo_entity','todo.shopping_list'))" 2>/dev/null || echo "todo.shopping_list")
export AUTO_SYNC_TODO=$(python3 -c "import json; d=json.load(open('$OPTS')); print(str(d.get('auto_sync_todo',False)).lower())" 2>/dev/null || echo "false")
export EXPOSE_SENSORS=$(python3 -c "import json; d=json.load(open('$OPTS')); print(str(d.get('expose_sensors',True)).lower())" 2>/dev/null || echo "true")

# Supervisor token is injected automatically by Home Assistant; pass it through
# so the app can call the Core API (set sensor states, sync the to-do list).
export SUPERVISOR_TOKEN="${SUPERVISOR_TOKEN}"

log_info "Language: $LANGUAGE"
log_info "Household: $HOUSEHOLD_NAME"
log_info "To-do entity: $TODO_ENTITY"
log_info "Expose sensors: $EXPOSE_SENSORS  Auto-sync: $AUTO_SYNC_TODO"
log_info "HA Core API: $([ -n "${SUPERVISOR_TOKEN}" ] && echo 'connected' || echo 'not available (standalone)')"
log_info "Starting server on port 8099..."

exec uvicorn app.main:app --host 0.0.0.0 --port 8099 --workers 1
