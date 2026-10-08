# Changelog

## 0.3.7 — اصلاحات امنیتی و استقرار

### امنیت
- **جستجوی پیشرفته**: با `include_shared=1` فقط اشتراک‌های دارای `can_view` و منقضی‌نشده برمی‌گردند (قبلاً فایل‌های بدون مجوز مشاهده یا منقضی هم نشت می‌کردند).
- **خروجی CSV گزارش Audit**: همه‌ی سلول‌ها گیومه‌گذاری می‌شوند و مقادیر شروع‌شده با `= + - @` خنثی می‌شوند (CSV/Formula injection).
- `SECURE_PROXY_SSL_HEADER` فقط با `TRUST_PROXY_SSL_HEADER=1` فعال می‌شود (قبلاً همیشه فعال بود و هدر قابل جعل بود).
- `docker-compose.yml`: رمز ادمین پیش‌فرض حذف شد؛ Postgres/Redis/MinIO/Backend/OnlyOffice فقط روی `127.0.0.1` منتشر می‌شوند.
- در حالت DEBUG فقط `media/avatars/` سرو می‌شود؛ فایل‌های خصوصی (`uploads/`) بدون احراز هویت در دسترس نیستند.

### رفع باگ
- ورودی نامعتبر (`limit`, `user`, تاریخ، حجم، پوشه) در Search/Audit اکنون ۴۰۰ می‌دهد، نه ۵۰۰.
- `date_to` به‌صورت `YYYY-MM-DD` اکنون کل همان روز را شامل می‌شود (در پایتون ۳.۱۱+ به نیمه‌شب تبدیل می‌شد).
- خلاصه‌ی (`summary`) گزارش Audit اکنون از همان فیلترهای درخواست پیروی می‌کند.
- کاربری که هم `auditor` و هم `support` است دیگر از Audit و فعالیت سازمانی محروم نمی‌شود (`role_for` فقط بالاترین نقش را می‌داد).
- اکشن `delete` به `ActivityLog.ACTION_CHOICES` اضافه شد (+ مایگریشن `0007`)، برچسب فارسی «حذف» نمایش داده می‌شود.
- با `DEBUG=0` healthcheck کانتینر دیگر به https ریدایرکت نمی‌شود (`SECURE_REDIRECT_EXEMPT`).
- فایل‌های استاتیک (ادمین Django) با WhiteNoise سرو می‌شوند.

### فرانت / استقرار
- خروجی CSV کل نتیجه‌ی فیلترشده را می‌گیرد (تا ۵٬۰۰۰ ردیف)، نه فقط ۲۰۰ ردیف نمایش‌داده‌شده.
- مسیر و لینک منوی `/audit` فقط برای owner / admin / auditor / superuser.
- `Dockerfile.frontend` اکنون build تولیدی + nginx (`nginx.conf`: SPA + پروکسی `/api`, `/ws`, `/admin`, `/static`).
- `vite.config.ts`: `allowedHosts` از `VITE_ALLOWED_HOSTS`؛ باقی‌مانده‌های Manus حذف شد.
- مستندات WebSocket Desk با رفتار واقعی (subprotocol) هماهنگ شد.

### تست
- `files/tests_search_audit.py`: دسترسی اشتراک، فیلترها، اعتبارسنجی ورودی، نقش‌های چندگانه، خلاصه‌ی فیلترشده.

### محدودیت‌های شناخته‌شده
- با `USE_S3=1` در docker-compose، URL آواتارها به `http://minio:9000` اشاره می‌کند که از مرورگر قابل دسترس نیست؛ برای production یک endpoint عمومی/پروکسی برای MinIO یا S3 واقعی لازم است.
- Logout با کوکی و `AllowAny` کار می‌کند؛ با `SameSite=None` باید محافظ CSRF اضافه شود.
