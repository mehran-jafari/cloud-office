# Cloud Office API

Development backend for the modular React frontend.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Endpoints:

- `GET /api/health/`
- `POST /api/auth/login/`
- `POST /api/auth/refresh/`
- `GET /api/auth/me/`
- `GET /api/files/items/`
- `GET /api/files/folders/`
- `GET /api/account/quota/`
- `GET /api/admin/users/`
- `PATCH /api/admin/users/<id>/quota/`
- `GET /api/admin/support-agents/`
- `PATCH /api/admin/support-agents/<id>/`
- `GET /api/support/conversations/`
- `POST /api/support/conversations/`
- `POST /api/support/conversations/<id>/messages/`

SQLite is the default for a zero-dependency local start. Set `USE_POSTGRES=1` in `.env` for PostgreSQL.

The production deployment checklist is in `../docs/production-deployment.md`.
