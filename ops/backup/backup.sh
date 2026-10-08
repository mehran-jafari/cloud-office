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
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
DEST="$BACKUP_ROOT/$STAMP"
mkdir -p "$DEST/db" "$DEST/minio"

POSTGRES_DB="${POSTGRES_DB:-cloud_office}"
POSTGRES_USER="${POSTGRES_USER:-cloud_office}"
MINIO_USER="${MINIO_ROOT_USER:-minioadmin}"
MINIO_PASSWORD="${MINIO_ROOT_PASSWORD:-change-me-minio-password}"
STORAGE_BUCKET="${AWS_STORAGE_BUCKET_NAME:-cloud-office}"

log() { printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*"; }
compose() { docker compose "$@"; }

log "Creating PostgreSQL custom-format dump"
compose exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$DEST/db/${POSTGRES_DB}.dump"

log "Mirroring MinIO application bucket"
compose run --rm --no-deps \
  -v "$DEST/minio:/backup/minio" \
  --entrypoint /bin/sh minio-init -c \
  "mc alias set source http://minio:9000 '$MINIO_USER' '$MINIO_PASSWORD' >/dev/null \
   && mc mirror --overwrite source/'$STORAGE_BUCKET' /backup/minio"

cat > "$DEST/manifest.txt" <<EOF
created_at_utc=$STAMP
postgres_database=$POSTGRES_DB
storage_bucket=$STORAGE_BUCKET
EOF

log "Writing checksums"
( cd "$DEST" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum ) > "$DEST/SHA256SUMS"

if [[ -n "${BACKUP_S3_ENDPOINT:-}" ]]; then
  : "${BACKUP_S3_ACCESS_KEY:?BACKUP_S3_ACCESS_KEY is required with BACKUP_S3_ENDPOINT}"
  : "${BACKUP_S3_SECRET_KEY:?BACKUP_S3_SECRET_KEY is required with BACKUP_S3_ENDPOINT}"
  : "${BACKUP_S3_BUCKET:?BACKUP_S3_BUCKET is required with BACKUP_S3_ENDPOINT}"
  log "Uploading backup to off-site S3-compatible storage"
  compose run --rm --no-deps \
    -v "$DEST:/backup/upload:ro" \
    -e BACKUP_S3_ENDPOINT -e BACKUP_S3_ACCESS_KEY -e BACKUP_S3_SECRET_KEY -e BACKUP_S3_BUCKET \
    --entrypoint /bin/sh minio-init -c \
    "mc alias set offsite \"$BACKUP_S3_ENDPOINT\" \"$BACKUP_S3_ACCESS_KEY\" \"$BACKUP_S3_SECRET_KEY\" >/dev/null \
     && mc cp --recursive /backup/upload offsite/\"$BACKUP_S3_BUCKET\"/cloud-office/$STAMP/"
fi

log "Removing local backups older than ${RETENTION_DAYS} days"
find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -mtime "+$RETENTION_DAYS" -print -exec rm -rf -- {} +
log "Backup completed: $DEST"
