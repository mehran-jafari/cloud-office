# Remote Support امن

Cloud Office اکنون یک جریان `Remote Support` دارد: کاربر یک کد ۸ رقمی کوتاه‌عمر می‌سازد، کارشناس مجاز با آن join می‌کند، و فقط بعد از رضایت صریح صاحب سیستم جلسه active می‌شود.

## API

```text
POST /api/support/remote-sessions/
POST /api/support/remote-sessions/join/
GET  /api/support/remote-sessions/<id>/
POST /api/support/remote-sessions/<id>/consent/
POST /api/support/remote-sessions/<id>/end/
```

## محدودیت عمدی MVP

این بخش session, consent, authorization و audit-friendly state را پیاده می‌کند؛ کنترل مخفی یا unattended access ندارد. برای مشاهده صفحه باید WebRTC با signaling Channels اضافه شود. برای کنترل واقعی ماوس/کیبورد سیستم‌عامل، یک Desktop Agent امضاشده با نصب و رضایت کاربر لازم است؛ مرورگر به‌تنهایی نباید کنترل unrestricted سیستم‌عامل را دریافت کند.

## مسیر Production

1. افزودن `RemoteSession` event log و TTL cleanup.
2. افزودن WebRTC signaling با Django Channels و Redis.
3. استفاده از `getDisplayMedia()` برای screen-share با permission مرورگر.
4. افزودن native agent فقط با pairing، code rotation، allow-list عملیات، audit log و دکمه‌ی قطع اضطراری.
5. rate limit برای ایجاد/join و عدم ثبت code خام در log.
