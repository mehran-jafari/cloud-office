# OnlyOffice backend integration

## Endpoints

- `GET /api/files/<id>/editor-config/` — authenticated owner/editor only.
- `GET /api/files/<id>/editor-download/?token=...` — short-lived signed download URL.
- `POST /api/files/<id>/onlyoffice-callback/` — provider callback authenticated with `X-OnlyOffice-Signature`.
- `GET /api/files/<id>/versions/` — authenticated version list.
- `POST /api/files/<id>/restore/<version>/` — authenticated restore.

## Local setup

```bash
cd backend
cp .env.example .env
python manage.py makemigrations files
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

Set `APP_PUBLIC_URL` to an address reachable from Document Server. The default `request.build_absolute_uri` is useful only when the provider can reach the same host.

## Callback security

The callback supports either native OnlyOffice JWT or an HMAC gateway signature. For native JWT, configure the same HS256 secret in Document Server and send `Authorization: Bearer <jwt>`. The callback body is authenticated using HMAC when a trusted reverse proxy or gateway adds:

```text
HMAC-SHA256(ONLYOFFICE_CALLBACK_SECRET, raw_request_body)
```

Send the lowercase hexadecimal digest in `X-OnlyOffice-Signature`, or prefix it with `sha256=`. In production, use a long random secret, HTTPS, and a network allow-list; do not rely on an unprotected public callback URL.

## Storage and scanning

The implementation uses Django `default_storage`, so it works with local storage and can later use S3/MinIO. Before enabling a new version as current in production, insert a malware scanner hook between `download_provider_file` and `default_storage.save`.

The current sample authorizes file owners. Replace `owned_file()` with the project’s central object-level permission service before enabling Viewer/Editor sharing.
