# Cloud Office (دفتر ابری) — نسخه 0.3.7

دفتر ابری سازمانی فارسی با React + Vite + Django REST + JWT + نقش‌های دسترسی + OnlyOffice + Remote Support (WebRTC).



## اتصال امن Desk (شبیه AnyDesk)

از معماری **DeskHost** ادغام شده است:

- شناسه **۹ رقمی** برای هر دستگاه/کاربر
- رمز اتصال قابل تعویض
- چند اتصال همزمان WebRTC
- دعوت به ویدیوکنفرانس با کد اتاق
- دفترچه آدرس و تاریخچه نشست

مسیر UI: `/remote-support` و `/video-conference`  
API: `/api/desk/` · WebSocket: `/ws/desk/` (توکن دستگاه از subprotocol: `['desk_token', '<token>']`؛ query string پشتیبانی نمی‌شود)

برای NAT سخت در production:

```env
TURN_URLS=turn:turn.example.com:3478
TURN_USERNAME=user
TURN_PASSWORD=secret
```

## هوش مصنوعی (فاز ۱ تا ۳)

| فاز | قابلیت | مسیر API |
|-----|--------|----------|
| ۱ | پیش‌نویس نامه، خلاصه متن، پیشنهاد پاسخ پشتیبانی | `/api/ai/draft-mail/`, `summarize/`, `support-reply/` |
| ۲ | گفتار به متن (STT) | `/api/ai/stt/` |
| ۳ | ایندکس معنایی فایل، جست‌وجوی معنایی، خلاصه جلسه | `/api/ai/index-file/`, `semantic-search/`, `meeting-summary/` |

بدون `AI_API_KEY` از **fallback محلی** استفاده می‌شود (دمو). با کلید OpenAI-compatible کیفیت کامل می‌شود:

```env
AI_API_KEY=sk-...
AI_BASE_URL=https://api.openai.com/v1
AI_CHAT_MODEL=gpt-4o-mini
AI_EMBED_MODEL=text-embedding-3-small
AI_STT_MODEL=whisper-1
```

سهمیه پیش‌فرض هر کاربر: ۲۰۰٬۰۰۰ توکن در ماه. Throttle: ۱۵ درخواست AI در دقیقه.

```bash
python manage.py migrate
```

## سخت‌سازی امنیتی (اعمال‌شده)

- **Throttle**: ناشناس ۳۰/دقیقه، کاربر ۱۲۰/دقیقه، login ۸/دقیقه، upload ۲۰/دقیقه
- **بدون mock فرانت**: خطای API واقعی نمایش داده می‌شود
- **دسترسی اشتراک**: دانلود/ویرایش/پیش‌نمایش بر اساس `can_download` / `can_edit` / `can_view`
- **آپلود**: لیست پسوند مجاز + سقف ۱۰۰MB
- **Production gate**: با `DEBUG=0` بدون `DJANGO_SECRET_KEY` قوی و `ALLOWED_HOSTS` اپ بالا نمی‌آید
- **docker-compose.yml**: Postgres + Redis برای استقرار نزدیک production

```bash
docker compose up -d   # db + redis
# سپس USE_POSTGRES=1 و REDIS_URL را در backend/.env بگذارید
```

## ویژگی‌های کلیدی
- احراز هویت امن (Access Token در memory + Refresh Token چرخشی در HttpOnly Cookie)
- نقش‌ها: owner / admin / support / auditor / member
- مدیریت فایل و پوشه + سهمیه فضا
- ویرایش آنلاین با OnlyOffice
- چت پشتیبانی + Remote Support امن با رضایت کاربر
- UI شیشه‌ای RTL + موبایل‌فرست

---


## اجرای سریع با یک دستور

### macOS / Linux
```bash
# فقط Backend
bash start-backend.sh

# فقط Frontend
bash start-frontend.sh

# هر دو با هم
bash start-all.sh
```

### Windows
دوبار کلیک یا:
```bat
start-all.bat
```
دو پنجره ترمینال جدا برای Backend و Frontend باز می‌شود.

## اجرای کامل با Docker برای تست Git

برای اجرای نزدیک به production با PostgreSQL، Redis، Django ASGI و Vite:

```bash
cp .env.example .env
# مقدار DJANGO_SUPERUSER_PASSWORD را در .env عوض کنید
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/api/health/
- نام کاربر پیش‌فرض: مقدار `DJANGO_SUPERUSER_USERNAME`
- رمز کاربر پیش‌فرض: مقدار `DJANGO_SUPERUSER_PASSWORD`

برای اجرای OnlyOffice اختیاری:

```bash
docker compose --profile office up --build
```

توقف و حذف containerها:

```bash
docker compose down
# حذف داده‌های PostgreSQL و فایل‌های محلی Docker:
docker compose down -v
```

در Git فقط `.env.example` را commit کنید؛ فایل `.env`، secretها، دیتابیس و فایل‌های media در `.gitignore` هستند.

### بررسی قبل از push

```bash
pnpm install --frozen-lockfile
pnpm typecheck
pnpm build
cd backend && python manage.py check && python manage.py test
cd .. && docker compose config
```

CI گیت‌هاب در `.github/workflows/ci.yml` همین بررسی‌ها را برای push و pull request اجرا می‌کند.

بار اول بعد از migrate در صورت نیاز:
```bash
cd backend && source .venv/bin/activate && python manage.py createsuperuser
```

## اجرای سریع (محلی / VS Code)

### پیش‌نیاز
- Python 3.11+
- Node.js 20+ (یا 22)
- pnpm (`npm i -g pnpm`) یا npm

### ۱. Backend (ترمینال اول)

```bash
cd backend
python3 -m venv .venv

# Windows:
# .venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # در صورت نیاز ویرایش کنید
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

> **نکته:** Redis لازم نیست. اگر `REDIS_URL` خالی باشد از InMemoryChannelLayer استفاده می‌شود.

### ۲. Frontend (ترمینال دوم)

```bash
# از ریشه پروژه
pnpm install
# یا: npm install

pnpm dev
# یا: npm run dev
```

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/api/health/
- API proxy خودکار از Vite به Django فعال است (`/api` → `:8000`)

### ورود اولیه
با کاربر `createsuperuser` وارد شوید. سپس از پنل مدیریت نقش‌ها و سهمیه‌ها را تنظیم کنید.

---

## اجرای Production (سرور)

راهنمای کامل در `docs/production-deployment.md` است.

خلاصه:
1. `pnpm build` → فایل‌های `dist/` را با Nginx سرو کنید.
2. Django را با Gunicorn/Uvicorn + Daphne پشت Nginx اجرا کنید.
3. PostgreSQL + Redis + OnlyOffice Document Server را پیکربندی کنید.
4. متغیرهای محیطی production را از `.env.example` پر کنید (`DJANGO_DEBUG=0`, `REFRESH_COOKIE_SECURE=1` و ...).

---

## ساختار پروژه

```
cloud-office/
├── src/                  # Frontend React
│   ├── api/              # لایه API + mock
│   ├── auth/             # AuthProvider + ProtectedRoute
│   ├── components/       # AppShell
│   ├── pages/            # صفحات
│   ├── hooks/            # WebSocket + WebRTC
│   └── routes/
├── backend/              # Django
│   ├── accounts/         # کاربران، نقش، سهمیه
│   ├── files/            # فایل‌ها + OnlyOffice
│   ├── support/          # چت + Remote Session
│   └── config/
├── docs/                 # راهنماها
└── package.json
```

---

## عیب‌یابی سریع

| مشکل | راه حل |
|------|--------|
| CORS / 401 | مطمئن شوید Vite proxy فعال است و cookie از همان origin می‌آید |
| WebSocket کار نمی‌کند | Redis را راه‌اندازی کنید یا `REDIS_URL` را خالی بگذارید (InMemory) |
| OnlyOffice | Document Server را جداگانه اجرا کنید و `ONLYOFFICE_URL` را تنظیم کنید |
| نصب pnpm | `npm install -g pnpm` |

---

نسخه: 0.3.7 — فهرست تغییرات در `CHANGELOG.md`  
تغییرات اصلی نسبت به 0.2:
- نسخه‌های پکیج قفل شد
- Vite proxy برای توسعه محلی
- InMemoryChannelLayer بدون نیاز به Redis
- حذف allowedHosts مربوط به Manus
- README و .env.example بهبود یافت

## تغییرات 0.3.5 (سخت‌سازی و رفع خطا برای استقرار)

- رفع SyntaxError در `ai/provider.py` که کل بک‌اند را از کار می‌انداخت.
- production: `ONLYOFFICE_CALLBACK_SECRET` باید ≥۳۲ نویسه و غیرپیش‌فرض باشد، وگرنه سرور بالا نمی‌آید.
- callback اونلی‌آفیس: فقط http/https و فقط میزبان Document Server (`ONLYOFFICE_URL` + `ONLYOFFICE_ALLOWED_HOSTS`)، بدون redirect؛ ویرایش فایل اشتراکی برای همکاران درست شد.
- دانلود inline فایل‌ها فقط برای انواع بی‌خطر (svg/html همیشه attachment) + `nosniff`.
- WebSocket: بررسی Origin، توکن فقط از subprotocol (query string حذف شد)، اتصال Desk اصلاح شد.
- پشتیبانی: AI فقط وقتی هیچ پشتیبان آنلاین (با مجوز پاسخ) نیست و انسان هنوز جواب نداده؛ بررسی سهمیه قبل از فراخوانی مدل؛ throttle پیام‌ها (`support_msg`)؛ escalation فقط برای تیکت‌های بدون پاسخ انسانی و حداکثر ۵ بار.
- رمزها با `AUTH_PASSWORD_VALIDATORS` اعتبارسنجی می‌شوند.
- فرانت: ادغام با نسخه complete (heartbeat حضور، پیام‌های pipeline، داشبورد عملکرد پشتیبان‌ها و دکمه اجرای escalation در پنل ادمین، رابط جدید گفتگو) با حفظ خلاصه‌سازی تیکت و گفتار به متن.
- Migration جدید: `ai/0002_alter_aiusagelog_action`. پس از به‌روزرسانی: `python manage.py migrate`.

## تغییرات 0.3.6 — نصب‌کننده عامل Desk (ویندوز/مک/لینوکس)

- علت کار نکردن: اسکریپت‌ها آدرس پیش‌فرض `localhost:3000` داشتند و روی سیستم مقصد به خود همان سیستم وصل می‌شدند؛ فایل‌های دانلودی هم در ویندوز (ExecutionPolicy/SmartScreen/انکودینگ فارسی) و مک (Gatekeeper، نبود مجوز اجرا) مسدود می‌شدند.
- اکنون اسکریپت‌ها از `GET /api/desk/agent/<windows|macos|linux>/?app=<origin>` ساخته می‌شوند و آدرس واقعی سرور داخلشان است (ورودی اعتبارسنجی و allow-list می‌شود).
- نصب با یک دستور (PowerShell / curl) از داخل دیالوگ برنامه؛ بدون دانلود فایل و بدون دسترسی ادمین.
- مک: ساخت `Cloud Office Desk.app` در `~/Applications`؛ ویندوز: میانبر Desktop و Start Menu؛ لینوکس: فایل `.desktop`. اجرای پنجره مستقل (Edge/Chrome/Brave) با fallback مرورگر پیش‌فرض.
- حذف نصب: ویندوز `CLOUD_OFFICE_UNINSTALL=1`، مک/لینوکس `| bash -s -- --uninstall`.
- production: `PUBLIC_APP_URL` را در `.env` تنظیم کنید.

## چک‌لیست استقرار

1. `backend/.env` را از `.env.example` بسازید؛ `DJANGO_DEBUG=0`، `DJANGO_SECRET_KEY` (≥۴۰ نویسه)، `DJANGO_ALLOWED_HOSTS`، `ONLYOFFICE_CALLBACK_SECRET`، `PUBLIC_APP_URL`، و در صورت نیاز `ONLYOFFICE_ALLOWED_HOSTS` (اگر Document Server در callback آدرسی غیر از `ONLYOFFICE_URL` برمی‌گرداند).
2. `pip install -r requirements.txt && python manage.py migrate && python manage.py check --deploy`
3. escalation پشتیبانی را با cron اجرا کنید: `python manage.py run_support_escalations` (هر ۵ دقیقه).
4. سرور ASGI (daphne/uvicorn) + Redis برای Channels؛ Origin وب‌سوکت باید در `CORS_ALLOWED_ORIGINS` یا `ALLOWED_HOSTS` باشد.
5. فقط کاربرانی با مجوز صریح «پاسخ‌گویی» می‌توانند آنلاین شوند/پاسخ دهند (superuser خودکار دارد).
