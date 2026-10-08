# CI/CD گیت‌هاب

## CI فعلی

فایل `.github/workflows/ci.yml` با هر `push` و `pull_request` اجرا می‌شود و این موارد را بررسی می‌کند:

- نصب lockfile frontend
- `pnpm typecheck`
- `pnpm build`
- نصب dependencyهای backend
- `python manage.py check`
- تمام تست‌های Django
- `docker compose config`

کلید واقعی AI در CI لازم نیست؛ workflow با `AI_API_KEY` و `OPENAI_API_KEY` خالی تست می‌کند.

## فعال‌سازی CI

1. repository را در GitHub بسازید.
2. کد را push کنید.
3. در تب Actions اجرای workflow را ببینید.
4. در Branch protection، پاس‌شدن jobهای CI را برای merge اجباری کنید.

## CD پیشنهادی

برای deployment واقعی، CI را با CD قاطی نکنید:

```text
Pull Request → CI فقط
merge به main → build image + deploy staging + smoke test
tag v* → approval → deploy production
```

برای GitHub Actions معمولاً این secrets لازم می‌شوند:

```text
REGISTRY_USERNAME
REGISTRY_TOKEN
DEPLOY_HOST
DEPLOY_USER
DEPLOY_SSH_KEY
STAGING_ENV_FILE یا secretهای جداگانه
PRODUCTION_ENV_FILE یا secretهای جداگانه
```

این secretها باید در GitHub Environments جداگانه به نام `staging` و `production` قرار بگیرند. `production` را با Required reviewers محافظت کنید.

## الگوی deployment روی سرور Docker

روی سرور، یک checkout ثابت داشته باشید و secretها را خارج از Git نگه دارید:

```bash
git clone https://github.com/ORG/REPO.git /opt/cloud-office
cd /opt/cloud-office
cp /opt/secrets/cloud-office.env .env
docker compose pull
docker compose run --rm backend python manage.py migrate --noinput
docker compose up -d --remove-orphans
a=0
until curl -fsS http://127.0.0.1:8000/api/health/; do
  a=$((a + 1)); test "$a" -lt 30 || exit 1; sleep 2
done
```

در production بهتر است imageها از GHCR با tag commit SHA دریافت شوند و `latest` استفاده نشود.

## قوانین مهم CD

- قبل از تعویض traffic، migration را اجرا کنید.
- backup دیتابیس و object storage را قبل از release بگیرید.
- بعد از deploy، health check، login، upload، editor-config و callback را smoke-test کنید.
- در صورت شکست health check، release قبلی را rollback کنید.
- `DJANGO_SECRET_KEY`، JWT، MinIO، AI و OnlyOffice secretها را در image یا Git قرار ندهید.
- برای OnlyOffice، URL عمومی callback باید از Document Server قابل دسترسی باشد.
- برای MinIO، bucket خصوصی و credential محدود به bucket استفاده کنید.

## CD واقعی نیازمند انتخاب مقصد است

فایل CI موجود است، اما deployment action را عمداً به یک سرور یا cloud خاص قفل نکرده‌ایم. برای تکمیل CD باید یکی از این مقصدها مشخص شود:

- Docker VM با SSH
- GitHub Container Registry + VM
- Kubernetes
- یک PaaS دارای Docker
- Cloud Run/ECS/اپراتور مشابه

پس از تعیین مقصد، workflow deploy باید فقط همان محیط را هدف بگیرد و secretهای همان محیط را بخواند.
