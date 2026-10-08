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

BACKUP_DIR="${1:-}"
if [[ -z "$BACKUP_DIR" || ! -d "$BACKUP_DIR" ]]; then
  echo "Usage: CONFIRM_RESTORE=YES $0 /absolute/path/to/backup" >&2
  exit 2
fi
if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Restore is destructive. Re-run with CONFIRM_RESTORE=YES." >&2
  exit 3
fi

POSTGRES_DB="${POSTGRES_DB:-cloud_office}"
POSTGRES_USER="${POSTGRES_USER:-cloud_office}"
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASSWORD="${MINIO_ROOT_PASSWORD:-change-me-minio-password}"
STORAGE_BUCKET="${AWS_STORAGE_BUCKET_NAME:-cloud-office}"

[[ -f "$BACKUP_DIR/SHA256SUMS" ]] || { echo "Missing SHA256SUMS" >&2; exit 4; }
( cd "$BACKUP_DIR" && sha256sum -c SHA256SUMS )

read -r -p "This replaces database '$POSTGRES_DB' and bucket '$STORAGE_BUCKET'. Type RESTORE to continue: " answer
[[ "$answer" == RESTORE ]] || { echo "Restore cancelled."; exit 5; }

echo "Restoring PostgreSQL"
docker compose exec -T db pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner < "$BACKUP_DIR/db/${POSTGRES_DB}.dump"

echo "Restoring MinIO bucket contents"
docker compose run --rm --no-deps \
  -v "$BACKUP_DIR/minio:/backup/minio:ro" \
  --entrypoint /bin/sh minio-init -c \
  "mc alias set target http://minio:9000 '$MINIO_USER' '$MINIO_PASSWORD' >/dev/null \
   && mc mb --ignore-existing target/'$STORAGE_BUCKET' \
   && mc mirror --overwrite /backup/minio target/'$STORAGE_BUCKET'"

echo "Restore completed. Run application smoke tests and verify object counts, login, uploads, and OnlyOffice callbacks."
