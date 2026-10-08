# مانیتورینگ و لاگ‌گیری متمرکز

## انتخاب stack

برای Docker Compose این پروژه از stack سبک زیر استفاده شده است:

- **Prometheus**: جمع‌آوری متریک و alert rule
- **Grafana**: داشبورد و نمایش متریک/لاگ
- **Loki**: ذخیره لاگ متمرکز
- **Promtail**: خواندن Docker JSON logs و ارسال به Loki
- **cAdvisor**: CPU، memory، network و container metrics
- **node-exporter**: متریک‌های host لینوکس

ELK برای حجم و جست‌وجوی بسیار بزرگ مناسب‌تر است، اما برای یک VM یا staging معمولاً RAM و disk بیشتری از این stack می‌خواهد.

## اجرای monitoring profile

```bash
cp .env.example .env
# حتماً GRAFANA_ADMIN_PASSWORD را تغییر دهید
docker compose --profile monitoring up -d
```

آدرس‌ها:

```text
Grafana:    http://localhost:3001
Prometheus: http://localhost:9090
Loki API:   http://localhost:3100
Django:     http://localhost:8000/api/metrics/
```

Grafana با datasourceهای Prometheus و Loki و یک dashboard اولیه provision می‌شود. در Explore برای لاگ‌ها query زیر را امتحان کنید:

```logql
{job="docker"}
```

در dashboard اولیه این موارد نمایش داده می‌شوند:

- نرخ request
- نرخ خطاهای 5xx
- p95 latency
- memory مصرفی containerها

## متریک Django

endpoint زیر برای Prometheus ایجاد شده است:

```text
GET /api/metrics/
```

متریک‌های اختصاصی:

```text
cloud_office_http_requests_total
cloud_office_http_request_duration_seconds
```

وقتی `METRICS_TOKEN` خالی باشد، endpoint فقط روی شبکه داخلی Compose قابل scrape است و برای local ساده است. در محیطی که endpoint عمومی یا از شبکه نامطمئن قابل دسترسی است، token قرار دهید و برای Prometheus از `authorization` با secret file استفاده کنید؛ endpoint metrics را public نکنید.

## لاگ‌گیری

Promtail فایل‌های Docker JSON logs را از این مسیر می‌خواند:

```text
/var/lib/docker/containers/*/*-json.log
```

برای این روش، Docker host باید دسترسی read-only به این مسیر را اجازه دهد. در Kubernetes یا محیط‌های managed، به‌جای این bind mount از collector همان پلتفرم استفاده کنید.

## نگهداری و alerting production

برای production این موارد را اضافه کنید:

- alert برای backend down، 5xx rate بالا، p95 latency بالا، disk پر، memory pressure، database unavailable، Redis unavailable و MinIO errors
- Alertmanager و notification channel مثل email/Slack/PagerDuty
- retention متریک و لاگ متناسب با حجم و policy
- backup برای volumeهای Prometheus، Grafana و Loki در صورت نیاز
- محدودکردن پورت‌های 9090، 3100 و 3001 به VPN یا شبکه داخلی
- HTTPS و authentication برای Grafana
- pin کردن همه imageها و بررسی CVE
- حذف secretها و tokenها از لاگ
- log rotation در Docker host

## Alerting با Telegram یا Slack

مسیر پیشنهادی production این است:

```text
Prometheus rules → Alertmanager → Telegram یا Slack
```

Grafana برای dashboard و Explore استفاده می‌شود. اگر تیم شما alertها را از داخل Grafana مدیریت می‌کند، می‌توانید Contact pointهای Grafana را جداگانه بسازید؛ اما برای ruleهای Prometheus این Alertmanager است که ارسال قابل‌اعتماد، grouping، silence و repeat interval را انجام می‌دهد.

### Telegram

1. در Telegram به `@BotFather` بروید و `/newbot` را اجرا کنید.
2. مقدار bot token را دریافت کنید.
3. bot را به گروه اضافه کنید یا به آن یک پیام بدهید.
4. `chat_id` را از updateهای Bot API یا یک bot کمکی پیدا کنید.
5. در `.env` تنظیم کنید:

```env
ALERTMANAGER_CONFIG=alertmanager.telegram.yml
TELEGRAM_BOT_TOKEN=123456:توکن-واقعی
TELEGRAM_CHAT_ID=-1001234567890
```

### Slack

1. در Slack یک Incoming Webhook برای channel موردنظر بسازید.
2. URL را در secret manager قرار دهید؛ این URL را در Git commit نکنید.
3. در `.env` تنظیم کنید:

```env
ALERTMANAGER_CONFIG=alertmanager.slack.yml
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_CHANNEL=alerts
```

فقط یکی از دو config را به‌عنوان `ALERTMANAGER_CONFIG` انتخاب کنید. token، chat ID و webhook باید فقط در `.env` یا secret manager باشند.

راه‌اندازی:

```bash
docker compose --profile monitoring up -d --force-recreate alertmanager prometheus
docker compose logs -f alertmanager prometheus
```

بررسی ruleها:

```bash
curl -fsS http://localhost:9090/api/v1/rules
curl -fsS http://localhost:9090/api/v1/alerts
curl -fsS http://localhost:9093/api/v2/status
```

برای تست بدون منتظرماندن ۵ دقیقه‌ای، در Prometheus یک rule موقت با `expr: vector(1)` بسازید، reload/restart کنید، ارسال پیام را ببینید و سپس rule را حذف کنید. در production این کار را با channel آزمایشی انجام دهید تا پیام اشتباه به تیم اصلی ارسال نشود.

Alertهای اولیه این پروژه:

- `CloudOfficeBackendDown`
- `CloudOfficeHigh5xxRate`
- `CloudOfficeHighP95Latency`
- `CloudOfficeMinioDown`
- `CloudOfficeContainerMemoryHigh`

در production، `group_wait`، `group_interval` و `repeat_interval` را با حساسیت سرویس تنظیم کنید و برای alertهای noisy از inhibition و silence استفاده کنید.

## تست smoke

```bash
docker compose ps
curl -fsS http://localhost:8000/api/health/
curl -fsS http://localhost:8000/api/metrics/ | grep cloud_office_http
docker compose logs --tail=100 backend promtail loki prometheus grafana
curl -fsS http://localhost:9093/api/v2/status
```

برای تولید یک sample metric، چند درخواست به health endpoint بفرستید و سپس در Prometheus query کنید:

```promql
sum(rate(cloud_office_http_requests_total[5m]))
```

## توقف و پاک‌سازی

```bash
docker compose --profile monitoring down
```

برای حذف داده‌های monitoring نیز volumeها را حذف کنید؛ این کار dashboards، history و logs را پاک می‌کند:

```bash
docker compose --profile monitoring down -v
```
