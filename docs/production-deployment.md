# Production deployment runbook

## Recommended architecture

```text
Nginx/HTTPS
  ├── /        → built React static files
  ├── /api/    → Django ASGI/WSGI service
  ├── /media/  → private object storage through Django signed URLs
  └── /ws/     → Django Channels/Redis when realtime chat is enabled
PostgreSQL + Redis + S3/MinIO + OnlyOffice Document Server
```

## 1. Build immutable artifacts

```bash
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
python3 -m pip install -r backend/requirements.txt
python3 backend/manage.py check --deploy
python3 backend/manage.py collectstatic --noinput
python3 backend/manage.py migrate --noinput
```

Serve `dist/` as static frontend assets. Run Django with Gunicorn/Uvicorn behind HTTPS; do not use `runserver` in production.

## 2. Required production environment

```env
DJANGO_DEBUG=0
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_ALLOWED_HOSTS=api.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com
REFRESH_COOKIE_SECURE=1
REFRESH_COOKIE_SAMESITE=Lax
CSRF_COOKIE_SECURE=1
SESSION_COOKIE_SECURE=1
USE_POSTGRES=1
DATABASE_NAME=cloud_office
DATABASE_USER=cloud_office
DATABASE_PASSWORD=<secret>
DATABASE_HOST=postgres
DATABASE_PORT=5432
VITE_API_URL=https://api.example.com/api
APP_PUBLIC_URL=https://api.example.com
ONLYOFFICE_URL=https://office.example.com
ONLYOFFICE_CALLBACK_SECRET=<long-random-secret>
```

Never commit `.env`, database passwords, JWT secrets, or provider tokens. Put them in the host secret manager.

## 3. Storage and quotas

Use S3/MinIO or another durable object store for `default_storage`; do not keep user files on ephemeral container disks. Keep `StorageQuota.allocated_bytes` as the administrator-controlled limit. All upload, editor callback, restore, and copy operations must check the quota atomically. Decide explicitly whether historical `FileVersion` objects count toward quota; the current MVP counts the current file size.

Run scheduled cleanup for orphaned objects and failed uploads. Add malware scanning before changing the current pointer.

## 4. Admin and support chat

The Django admin manages users, quotas, conversations, and `SupportAgentPermission`. The API also exposes:

- `GET /api/admin/users/`
- `PATCH /api/admin/users/<id>/quota/`
- `GET /api/admin/support-agents/`
- `PATCH /api/admin/support-agents/<id>/`
- `GET/POST /api/support/conversations/`
- `POST /api/support/conversations/<id>/messages/`

Only staff can access administrative lists. Only a superuser can grant or revoke support reply permission. A staff user without an explicit permission receives `403` when attempting to reply.

For true live chat, add Django Channels + Redis, connection authentication, message rate limits, unread counters, and a notification provider. The current MVP provides authenticated persisted chat with immediate API refresh.

## 5. OnlyOffice

The Document Server must reach the public callback and signed download URLs over HTTPS. Configure the same callback JWT/HMAC secret, restrict network access, and verify the callback key/revision. Set a reverse proxy timeout suitable for document saves. Test DOCX/XLSX/PPTX save, quota rejection, duplicate callbacks, restore, and provider outage.

## 6. Operational requirements

- Run migrations as a release step before switching traffic.
- Add health checks for Django, PostgreSQL, Redis, object storage, and OnlyOffice.
- Centralize JSON logs without passwords, tokens, document contents, or signed URLs.
- Back up PostgreSQL and object storage; test restore.
- Add rate limiting for login, chat message, callback, and download endpoints.
- Monitor storage usage, quota rejection, callback failures, queue latency, and 5xx responses.
- Use separate staging and production secrets and databases.
- Rotate JWT, callback, and database credentials without rebuilding source code.
