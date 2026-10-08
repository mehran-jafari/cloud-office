#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

BACKUP_ROOT="${BACKUP_ROOT:-$ROOT_DIR/backups}"
DRILL_PROJECT="${RESTORE_DRILL_PROJECT:-cloud-office-staging-drill}"
DRILL_BACKEND_PORT="${RESTORE_DRILL_BACKEND_PORT:-18000}"
DRILL_MINIO_API_PORT="${RESTORE_DRILL_MINIO_API_PORT:-19000}"
DRILL_MINIO_CONSOLE_PORT="${RESTORE_DRILL_MINIO_CONSOLE_PORT:-19001}"
REPORT_DIR="${BACKUP_ROOT}/restore-drills"
REPORT="$REPORT_DIR/$(date -u +%Y%m%dT%H%M%SZ)-${DRILL_PROJECT}.report"
mkdir -p "$REPORT_DIR"

BACKUP_DIR="${RESTORE_DRILL_BACKUP_DIR:-}"
if [[ -z "$BACKUP_DIR" ]]; then
  BACKUP_DIR="$(find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d ! -name restore-drills -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)"
fi

log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$REPORT"; }

notify() {
  local status="$1"
  local summary="$2"
  local message
  message="$(printf 'Cloud Office Restore Drill: %s\n%s\nProject: %s\nReport: %s' "$status" "$summary" "$DRILL_PROJECT" "$REPORT")"

  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" && "${TELEGRAM_CHAT_ID}" != "0" ]]; then
    curl -fsS --max-time 15 -X POST \
      "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      --data-urlencode "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${message}" >/dev/null || true
  fi

  if [[ -n "${SLACK_WEBHOOK_URL:-}" ]]; then
    local payload
    payload="$(python3 - "$message" <<'PY'
import json
import sys
print(json.dumps({'text': sys.argv[1]}))
PY
)"
    curl -fsS --max-time 15 -X POST \
      -H 'Content-Type: application/json' \
      --data "$payload" "$SLACK_WEBHOOK_URL" >/dev/null || true
  fi
}

cleanup() {
  if [[ "${KEEP_RESTORE_DRILL:-0}" != "1" ]]; then
    docker compose -p "$DRILL_PROJECT" down -v --remove-orphans >>"$REPORT" 2>&1 || true
  fi
}

on_exit() {
  local status=$?
  if [[ "$status" -eq 0 ]]; then
    notify "PASSED" "Checksum, restore, Django check, health, metrics, and database smoke tests passed."
  else
    notify "FAILED" "Restore drill exited with code ${status}. Review the report and staging logs."
  fi
  cleanup
  exit "$status"
}

trap on_exit EXIT
: > "$REPORT"

if [[ -z "$BACKUP_DIR" || ! -d "$BACKUP_DIR" ]]; then
  log "No backup directory found"
  exit 2
fi

export COMPOSE_PROJECT_NAME="$DRILL_PROJECT"
export BACKEND_PORT="$DRILL_BACKEND_PORT"
export MINIO_API_PORT="$DRILL_MINIO_API_PORT"
export MINIO_CONSOLE_PORT="$DRILL_MINIO_CONSOLE_PORT"
export USE_S3="${USE_S3:-1}"

log "Starting restore drill project=$DRILL_PROJECT backup=$BACKUP_DIR"
log "Starting isolated staging dependencies"
docker compose -p "$DRILL_PROJECT" up -d db redis minio minio-init backend >>"$REPORT" 2>&1

log "Restoring backup and verifying checksums"
printf 'RESTORE\n' | CONFIRM_RESTORE=YES ./ops/backup/restore.sh "$BACKUP_DIR" >>"$REPORT" 2>&1

log "Running Django checks"
docker compose -p "$DRILL_PROJECT" exec -T backend python manage.py check >>"$REPORT" 2>&1

log "Waiting for backend health"
for attempt in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${DRILL_BACKEND_PORT}/api/health/" >>"$REPORT" 2>&1; then
    printf '\n' >>"$REPORT"
    break
  fi
  [[ "$attempt" -lt 30 ]] || { log "Backend health check failed"; exit 1; }
  sleep 2
done

log "Checking metrics endpoint"
metrics_args=()
if [[ -n "${METRICS_TOKEN:-}" ]]; then
  metrics_args=(-H "Authorization: Bearer ${METRICS_TOKEN}")
fi
curl -fsS "${metrics_args[@]}" "http://127.0.0.1:${DRILL_BACKEND_PORT}/api/metrics/" | grep -q 'cloud_office_http' || {
  log "Metrics smoke check failed"
  exit 1
}

log "Checking restored database connectivity"
docker compose -p "$DRILL_PROJECT" exec -T backend python manage.py shell -c \
  "from files.models import File; print('restored_files=' + str(File.objects.count()))" >>"$REPORT" 2>&1

log "RESTORE DRILL PASSED"
