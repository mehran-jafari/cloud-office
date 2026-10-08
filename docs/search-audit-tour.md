# جستجوی پیشرفته، Audit و راهنمای شروع

## جستجوی پیشرفته
- API: `GET /api/files/search/?q=&type=&folder=&date_from=&date_to=&min_size=&max_size=&include_shared=1`
- type: `pdf|doc|sheet|image|video|audio`
- UI: صفحه فایل‌ها → دکمه «جست‌وجوی پیشرفته»

## گزارش Audit
- API: `GET /api/files/audit/?action=&user=&q=&date_from=&date_to=&limit=200`
- دسترسی: owner / admin / auditor
- UI: `/audit` + خروجی CSV

## راهنمای درون‌برنامه‌ای (Tour)
- اولین ورود به‌صورت خودکار نمایش داده می‌شود
- ذخیره در `localStorage` کلید `cloud-office-tour-done-v1`
- اجرای دوباره: دکمه «راهنمای شروع» در پایین سایدبار
