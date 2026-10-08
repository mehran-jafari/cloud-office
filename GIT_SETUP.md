# راه‌اندازی در Git و اجرای محیط تست

## وضعیت این نسخه

این نسخه برای اجرای تستی آماده شده است:

- frontend: React + Vite
- backend: Django + Daphne
- database: PostgreSQL در Compose
- realtime: Redis + Django Channels
- تست backend: ۲۳ تست موجود پاس می‌شوند
- بررسی frontend: `typecheck` و `build` پاس می‌شوند
- CI: گیت‌هاب اکشن در `.github/workflows/ci.yml`
- AI، ایمیل، TURN و OnlyOffice به‌صورت تنظیم‌پذیر هستند و credential واقعی داخل repository قرار نگرفته است.

## قرار دادن در GitHub یا GitLab

از ریشه پروژه:

```bash
git init
git add .
git commit -m "Prepare Cloud Office for local test deployment"
git branch -M main
git remote add origin https://github.com/ORG/REPO.git
git push -u origin main
```

قبل از `git add` بررسی کنید که `.env`، دیتابیس، فایل‌های media و `node_modules` وارد Git نشده باشند:

```bash
git status --ignored
```

## اجرای پیشنهادی تستی

```bash
cp .env.example .env
# حداقل DJANGO_SUPERUSER_PASSWORD و POSTGRES_PASSWORD را تغییر دهید
docker compose up --build
```

آدرس‌ها:

- frontend: `http://localhost:3000`
- backend health: `http://localhost:8000/api/health/`
- کاربر پیش‌فرض: مقادیر `DJANGO_SUPERUSER_USERNAME` و `DJANGO_SUPERUSER_PASSWORD` در `.env`

برای OnlyOffice:

```bash
docker compose --profile office up --build
```

در حالت عادی بدون profile، برنامه بالا می‌آید اما ویرایش OnlyOffice در دسترس نیست.

## تست‌های قبل از push

```bash
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build

cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
AI_API_KEY= OPENAI_API_KEY= python manage.py check
AI_API_KEY= OPENAI_API_KEY= python manage.py test
cd ..

docker compose config
```

## مواردی که عمداً نیاز به تنظیم بیرونی دارند

این موارد بدون اطلاعات سرویس واقعی قابل فعال‌سازی امن نیستند:

- `AI_API_KEY` برای مدل‌های خارجی؛ بدون آن fallback محلی استفاده می‌شود.
- SMTP یا provider پیامک برای اعلان‌ها.
- S3/MinIO production برای فایل‌های دائمی.
- TURN server برای WebRTC در شبکه‌های سخت NAT.
- دامنه HTTPS، secret manager و backup واقعی برای production.
- OnlyOffice production با callback عمومی و secret مشترک.

## نکته production

Compose این فایل برای **تست و staging کوچک** است. برای production باید secretها در secret manager باشند، HTTPS و reverse proxy فعال شود، backup و restore آزمایش شود و imageها با نسخه ثابت deploy شوند. `runserver` فقط برای توسعه است؛ image backend این نسخه با Daphne اجرا می‌شود.
