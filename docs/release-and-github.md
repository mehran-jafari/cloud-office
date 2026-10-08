# خروجی کامل پروژه و راه‌اندازی روی GitHub

## محتویات release

این release شامل backend، frontend، Docker Compose و integrationهای زیر است:

```text
backend/
├── config/              تنظیمات Django، URLها، ASGI و production config
├── accounts/            احراز هویت، کاربران، نقش‌ها و سهمیه
├── files/               فایل‌ها، upload/download، اشتراک و versioning
├── ai/                  provider سازگار با OpenAI، quota و usage log
├── support/             پشتیبانی و پیام‌ها
├── desk/                desk، session و installerها
├── monitoring.py        middleware متریک HTTP
├── monitoring_views.py  endpoint /api/metrics/
├── Dockerfile
└── entrypoint.sh

src/
├── api/                 API client و auth
├── auth/                AuthProvider و session
├── components/          editorها، dashboard و UI
├── pages/               route/pageهای frontend
└── styles.css

monitoring/
├── prometheus/          scrape config و alert rules
├── grafana/             datasource و dashboard provisioning
├── loki/                centralized logs
├── promtail/            Docker log collector
└── alertmanager/        Telegram و Slack templates

ops/backup/
├── backup.sh            PostgreSQL + MinIO backup
├── restore.sh           restore محافظت‌شده
├── restore-drill.sh     Restore Drill ایزوله staging
├── *.service            systemd services
└── *.timer              systemd schedules

.github/workflows/ci.yml  تست frontend/backend و Compose validation
docker-compose.yml        db، redis، backend، frontend، MinIO، OnlyOffice، monitoring
docs/                     راهنماهای AI، OnlyOffice، CI/CD، monitoring و DR
```

## راه‌اندازی با Docker

```bash
git clone https://github.com/YOUR_USERNAME/cloud-office.git
cd cloud-office
cp .env.example .env
```

در `.env` حداقل این‌ها را تغییر دهید:

```env
DJANGO_SECRET_KEY=یک-کلید-تصادفی-طولانی
DJANGO_SUPERUSER_PASSWORD=یک-رمز-قوی
MINIO_ROOT_PASSWORD=یک-رمز-قوی
ONLYOFFICE_CALLBACK_SECRET=یک-کلید-تصادفی-طولانی
GRAFANA_ADMIN_PASSWORD=یک-رمز-قوی
```

برای اجرای اصلی:

```bash
docker compose up -d --build
```

برای OnlyOffice:

```bash
docker compose --profile office up -d
```

برای Monitoring:

```bash
docker compose --profile monitoring up -d
```

برای اجرای کامل:

```bash
docker compose --profile office --profile monitoring up -d --build
```

آدرس‌های local:

```text
Frontend:    http://localhost:3000
Backend:     http://localhost:8000
Health:      http://localhost:8000/api/health/
Metrics:     http://localhost:8000/api/metrics/
OnlyOffice:  http://localhost:8080
Grafana:      http://localhost:3001
Prometheus:   http://localhost:9090
Alertmanager: http://localhost:9093
MinIO:        http://localhost:9001
```

## اجرای تست‌ها

```bash
cd backend
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
AI_API_KEY= OPENAI_API_KEY= python manage.py check
AI_API_KEY= OPENAI_API_KEY= python manage.py test

cd ..
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
python3 - <<'PY'
import yaml
with open('docker-compose.yml') as f:
    yaml.safe_load(f)
print('Compose YAML OK')
PY
```

## قراردادن در GitHub از ZIP

1. از GitHub یک repository خالی بسازید؛ مثلاً `cloud-office`.
2. ZIP را extract کنید.
3. وارد ریشه‌ای شوید که `.git` و `docker-compose.yml` دارد.
4. remote را اضافه کنید:

```bash
git remote add origin https://github.com/YOUR_USERNAME/cloud-office.git
git branch -M main
git push -u origin main
```

اگر local Git از قبل وجود دارد، `git init` دوباره اجرا نکنید.

## قراردادن در GitHub از Git Bundle

```bash
mkdir cloud-office
cd cloud-office
git clone /path/to/cloud-office-git-ready-v0_3_6.bundle .
git remote add origin https://github.com/YOUR_USERNAME/cloud-office.git
git push -u origin main
```

## CI در GitHub

بعد از push، فایل زیر خودکار اجرا می‌شود:

```text
.github/workflows/ci.yml
```

این workflow اجرا می‌کند:

- frontend dependency install
- TypeScript typecheck
- frontend production build
- backend dependency install
- Django check
- تمام Django tests
- Compose configuration validation

در GitHub از مسیر زیر branch protection را فعال کنید:

```text
Settings → Branches → Add branch protection rule
```

برای `main` گزینه **Require status checks before merging** را فعال کنید.

## Secretهای GitHub

مقادیر واقعی را در repository قرار ندهید. برای deployment از GitHub Environments استفاده کنید:

```text
staging
production
```

Secretهای اصلی:

```text
DJANGO_SECRET_KEY
DJANGO_SUPERUSER_PASSWORD
MINIO_ROOT_PASSWORD
ONLYOFFICE_CALLBACK_SECRET
AI_API_KEY
GRAFANA_ADMIN_PASSWORD
TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID
SLACK_WEBHOOK_URL
BACKUP_S3_ACCESS_KEY
BACKUP_S3_SECRET_KEY
```

## Backup و Restore Drill روی staging

```bash
./ops/backup/backup.sh
./ops/backup/restore-drill.sh
```

زمان‌بندی backup روزانه:

```bash
sudo cp ops/backup/cloud-office-backup.service /etc/systemd/system/
sudo cp ops/backup/cloud-office-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cloud-office-backup.timer
```

زمان‌بندی Restore Drill هفتگی:

```bash
sudo cp ops/backup/cloud-office-restore-drill.service /etc/systemd/system/
sudo cp ops/backup/cloud-office-restore-drill.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cloud-office-restore-drill.timer
```

نتیجه drill به این متغیرها ارسال می‌شود:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
SLACK_WEBHOOK_URL=...
```

## production checklist

قبل از انتشار production:

- HTTPS برای frontend، backend و OnlyOffice
- secret manager
- PostgreSQL backup و PITR برای RPO کم
- MinIO versioning و off-site backup
- Grafana پشت VPN یا reverse proxy
- Alertmanager به Telegram/Slack
- branch protection و CI سبز
- Restore Drill موفق در staging
- database migration plan
- rollback image با commit SHA
- backup و restore واقعی، نه فقط syntax check
