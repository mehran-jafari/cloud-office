# اتصال AI و MinIO

## AI واقعی

Backend از API سازگار با OpenAI استفاده می‌کند و این endpointها را لازم دارد:

- `POST /chat/completions`
- `POST /embeddings`
- `POST /audio/transcriptions`

در `.env`:

```env
AI_API_KEY=کلید-واقعی-سرویس
AI_BASE_URL=https://api.openai.com/v1
AI_CHAT_MODEL=gpt-4o-mini
AI_EMBED_MODEL=text-embedding-3-small
AI_STT_MODEL=whisper-1
```

برای provider سازگار دیگر فقط `AI_BASE_URL` و نام مدل‌ها عوض می‌شود. اگر کلید خالی باشد fallback محلی فعال می‌ماند. کلید را در Git commit نکنید.

در Compose این متغیرها به backend پاس داده می‌شوند. بعد از تغییر `.env`:

```bash
docker compose up -d --build backend
```

برای اطمینان از اتصال، از داخل container درخواست‌های AI را با endpoint واقعی بررسی کنید و log خطای `401` یا `404` را بررسی کنید. سرویس‌های local که فقط chat دارند ممکن است embedding یا STT را پشتیبانی نکنند؛ در این حالت برای آن قابلیت‌ها provider جدا لازم است.

## MinIO

Compose این پروژه سه سرویس را اضافه می‌کند:

- `minio`: API روی پورت 9000 و Console روی پورت 9001
- `minio-init`: ساخت bucket و خصوصی‌کردن آن
- `backend`: استفاده از `django-storages` و boto3 از طریق `default_storage`

تنظیمات تستی:

```env
USE_S3=1
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=یک-رمز-قوی
AWS_STORAGE_BUCKET_NAME=cloud-office
AWS_S3_ENDPOINT_URL=http://minio:9000
AWS_S3_REGION_NAME=us-east-1
AWS_S3_ADDRESSING_STYLE=path
AWS_S3_SIGNATURE_VERSION=s3v4
AWS_QUERYSTRING_AUTH=1
AWS_QUERYSTRING_EXPIRE=900
```

اجرا:

```bash
cp .env.example .env
docker compose up --build
```

پنل MinIO:

```text
http://localhost:9001
```

با `MINIO_ROOT_USER` و `MINIO_ROOT_PASSWORD` وارد شوید. bucket `cloud-office` خودکار ساخته می‌شود. فایل‌ها خصوصی باقی می‌مانند و backend برای دانلود، signed URL یا stream کنترل‌شده صادر می‌کند.

## MinIO production

در production:

- از `latest` استفاده نکنید؛ نسخه image را pin کنید.
- root credential را برای برنامه استفاده نکنید؛ یک access key محدود به bucket بسازید.
- MinIO را پشت HTTPS و reverse proxy قرار دهید.
- `AWS_S3_ENDPOINT_URL` را به آدرس داخلی/خصوصی MinIO بدهید.
- backup و versioning bucket را فعال کنید.
- lifecycle برای فایل‌های موقت و orphan تنظیم کنید.
- bucket را public نکنید.
- `AWS_QUERYSTRING_EXPIRE` را کوتاه نگه دارید.
- برای فایل‌های حساس، malware scanning قبل از ثبت نهایی انجام دهید.

## تفاوت local و production

در اجرای بدون `USE_S3=1`، Django از `MEDIA_ROOT` محلی استفاده می‌کند. در Docker Compose پیش‌فرض تستی، MinIO فعال است. در production بهتر است `USE_S3=1`، PostgreSQL، Redis، HTTPS و secret manager هم‌زمان فعال باشند.
