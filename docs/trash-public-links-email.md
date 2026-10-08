# سطل زباله، لینک عمومی و اعلان ایمیل

نسخه ۰.۳.۷+ — سه قابلیت اضافه‌شده:

## ۱. سطل زباله (Trash)

حذف فایل/پوشه دیگر دائمی نیست و به سطل زباله منتقل می‌شود.

| متد | مسیر | توضیح |
|-----|------|--------|
| GET | `/api/files/trash/` | لیست آیتم‌های سطل زباله |
| POST | `/api/files/trash/restore/` | بازیابی `{file_ids, folder_ids}` |
| POST | `/api/files/trash/purge/` | حذف دائمی یا `{empty_all: true}` |

عملیات `bulk` با `action=delete` الان soft-delete انجام می‌دهد.

## ۲. لینک عمومی با انقضا و رمز

| متد | مسیر | توضیح |
|-----|------|--------|
| GET/POST | `/api/files/public-links/` | لیست / ساخت لینک |
| PATCH/DELETE | `/api/files/public-links/<id>/` | ویرایش / لغو |
| POST/GET | `/api/files/public/share/<token>/` | دسترسی عمومی (بدون لاگین) |

بدنه ساخت لینک نمونه:

```json
{
  "file": 12,
  "permission": "download",
  "expires_at": "2026-12-31T23:59:00Z",
  "max_downloads": 10,
  "password": "optional-secret",
  "note": "برای پیمانکار"
}
```

## ۳. اعلان ایمیل

با تنظیم `EMAIL_HOST` و مربوطه در `.env`، اعلان اشتراک فایل به‌صورت ایمیل هم ارسال می‌شود.

```env
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_USE_TLS=1
DEFAULT_FROM_EMAIL=Cloud Office <noreply@example.com>
NOTIFY_EMAIL_ON_ALL=0
```

بدون `EMAIL_HOST` فقط اعلان درون‌برنامه‌ای ساخته می‌شود.

## Migration

```bash
python manage.py migrate files
```
