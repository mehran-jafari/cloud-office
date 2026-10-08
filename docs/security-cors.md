# Security and CORS configuration

## Runtime origins

React calls Django through `VITE_API_URL`. Django allows only the exact frontend origin in `CORS_ALLOWED_ORIGINS`; do not use `*` when credentials are enabled. The same exact origins belong in `CSRF_TRUSTED_ORIGINS` for unsafe browser requests.

Example for an HTTPS deployment (replace with your own domains):

```env
VITE_API_URL=https://office.example.com/api
CORS_ALLOWED_ORIGINS=https://office.example.com
CSRF_TRUSTED_ORIGINS=https://office.example.com
DJANGO_ALLOWED_HOSTS=office.example.com
# behind a TLS-terminating reverse proxy that overwrites X-Forwarded-Proto:
TRUST_PROXY_SSL_HEADER=1
REFRESH_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
SESSION_COOKIE_SECURE=1
```

`TRUST_PROXY_SSL_HEADER` must stay `0` (default) when Django is reachable directly, because clients could otherwise forge `X-Forwarded-Proto`.

## Cookie policy

Access tokens remain in React memory. The refresh token is an `HttpOnly` cookie with a restricted `/api/auth/` path. HTTPS deployments use `Secure=1`; local HTTP uses `Secure=0`. `SameSite=Lax` is appropriate when frontend and API are same-site. Use `SameSite=None` only when they are genuinely cross-site, and then require `Secure=1`.

## Verification performed

- Public API health returned HTTP 200.
- `OPTIONS /api/auth/login/` returned the exact frontend `Access-Control-Allow-Origin` and `Access-Control-Allow-Credentials: true`.
- Credentialed `POST /api/auth/login/` with the `Admin` account returned HTTP 200, an access token, and an HttpOnly/SameSite refresh cookie.
- Public frontend returned HTTP 200.

Before production, replace development secrets, enable `DJANGO_DEBUG=0`, use HTTPS only, add a real reverse proxy, rotate the callback/JWT secrets, and restrict `DJANGO_ALLOWED_HOSTS` to the deployed API hostname.
