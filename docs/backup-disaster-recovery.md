# Backup و Disaster Recovery

## سیاست پایه پیشنهادی

برای این پلتفرم از قاعده **3-2-1** استفاده کنید:

- حداقل ۳ کپی از داده
- روی حداقل ۲ نوع storage
- حداقل ۱ کپی خارج از سرور اصلی و ترجیحاً immutable

دامنه backup:

1. **PostgreSQL**: dump سازگار با application، نه فقط snapshot خام volume.
2. **MinIO/S3**: objectها، نسخه‌ها و metadata؛ bucket versioning در production فعال باشد.
3. **تنظیمات و secret references**: کد و Compose در Git؛ secret واقعی در secret manager؛ از `.env` backup امن و رمزنگاری‌شده فقط در صورت ضرورت.
4. **Monitoring**: Grafana dashboards، alert rules و provisioning در Git؛ history Prometheus/Loki معمولاً قابل بازسازی است و الزاماً backup روزانه نیست.

## RPO/RTO پیشنهادی

برای شروع staging/production کوچک:

| داده | برنامه | RPO هدف | RTO هدف |
|---|---|---:|---:|
| PostgreSQL | هر ۶۰ دقیقه یا حداقل روزانه | ۱ ساعت | ۱–۲ ساعت |
| MinIO objects | mirror روزانه + versioning | ۲۴ ساعت | ۲–۴ ساعت |
| Git/config | هر commit در remote | نزدیک صفر | ۳۰ دقیقه |
| Monitoring config | هر commit در remote | نزدیک صفر | ۱ ساعت |

برای داده‌های حساس یا تراکنش زیاد، PostgreSQL WAL archiving/PITR و replication را به جای dump روزانه اضافه کنید.

## اجرای backup دستی

پیش‌نیاز: سرویس‌های PostgreSQL، backend و MinIO بالا باشند.

```bash
cp .env.example .env
# BACKUP_ROOT و BACKUP_RETENTION_DAYS را تنظیم کنید
./ops/backup/backup.sh
```

اسکریپت:

- از PostgreSQL با `pg_dump -Fc` dump می‌گیرد.
- bucket برنامه را با `mc mirror` کپی می‌کند.
- manifest و SHA256 checksum می‌سازد.
- backupهای local قدیمی را طبق retention پاک می‌کند.
- اگر `BACKUP_S3_ENDPOINT` تنظیم شده باشد، خروجی را به مقصد off-site S3-compatible می‌فرستد.

مقصد off-site نمونه:

```env
BACKUP_S3_ENDPOINT=https://s3.example.com
BACKUP_S3_ACCESS_KEY=backup-only-access-key
BACKUP_S3_SECRET_KEY=backup-only-secret
BACKUP_S3_BUCKET=cloud-office-backups
BACKUP_RETENTION_DAYS=30
```

برای S3 واقعی، access key را فقط به bucket backup محدود کنید و object lock/immutability را طبق policy فعال کنید.

## زمان‌بندی خودکار با systemd

فایل‌های template در `ops/backup/` هستند. روی VM:

```bash
sudo cp ops/backup/cloud-office-backup.service /etc/systemd/system/
sudo cp ops/backup/cloud-office-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cloud-office-backup.timer
systemctl list-timers cloud-office-backup.timer
```

زمان پیش‌فرض هر روز ساعت ۰۲:۰۰ با کمی تأخیر تصادفی است. برای hourly backup، `OnCalendar=hourly` را با توجه به RPO انتخاب کنید.

## بررسی backup

بعد از هر اجرا:

```bash
find "$BACKUP_ROOT" -maxdepth 2 -type f | sort
cat "$BACKUP_ROOT/<timestamp>/manifest.txt"
( cd "$BACKUP_ROOT/<timestamp>" && sha256sum -c SHA256SUMS )
```

موفقیت اجرای script به‌تنهایی کافی نیست؛ باید restore واقعی انجام شود.

## Restore و Disaster Recovery

این عملیات destructive است. ابتدا سرویس‌ها را از traffic خارج کنید، backup صحیح را انتخاب کنید، و قبل از restore snapshot/backup وضعیت فعلی را بگیرید.

```bash
CONFIRM_RESTORE=YES ./ops/backup/restore.sh /absolute/path/to/backups/<timestamp>
```

اسکریپت دو بار تأیید می‌خواهد:

- `CONFIRM_RESTORE=YES`
- تایپ‌کردن `RESTORE`

سپس:

1. checksum را بررسی می‌کند.
2. PostgreSQL را restore می‌کند.
3. objectهای MinIO را mirror می‌کند.
4. نیاز به smoke test بعد از restore را اعلام می‌کند.

Smoke test:

```bash
curl -fsS http://localhost:8000/api/health/
# login را تست کنید
# upload و download یک فایل را تست کنید
# editor-config و OnlyOffice callback را تست کنید
# version list و restore version را تست کنید
docker compose ps
```

## Restore drill

حداقل ماهانه در staging:

1. یک backup واقعی انتخاب کنید.
2. یک محیط جدا با نام/volume جدا بسازید.
3. PostgreSQL و MinIO را restore کنید.
4. checksum، تعداد objectها و تعداد رکوردهای کلیدی را مقایسه کنید.
5. login، upload، download، AI، OnlyOffice و version restore را تست کنید.
6. زمان واقعی restore را ثبت کنید.
7. نتیجه و نقص‌ها را در issue یا runbook ثبت کنید.

## Restore Drill خودکار در Staging

فایل `ops/backup/restore-drill.sh` یک پروژه Compose ایزوله با نام جدا می‌سازد؛ بنابراین volumeهای staging اصلی را overwrite نمی‌کند. این script:

1. آخرین backup را انتخاب می‌کند یا `RESTORE_DRILL_BACKUP_DIR` را استفاده می‌کند.
2. سرویس‌های `db`، `redis`، `minio` و `backend` را با project name جدا بالا می‌آورد.
3. checksum را بررسی و PostgreSQL/MinIO را restore می‌کند.
4. `manage.py check`، health endpoint، metrics endpoint و اتصال database را تست می‌کند.
5. report متنی در `backups/restore-drills/` می‌نویسد.
6. در پایان project و volumeهای drill را حذف می‌کند؛ با `KEEP_RESTORE_DRILL=1` برای اشکال‌زدایی نگه می‌دارد.

اجرای دستی:

```bash
./ops/backup/restore-drill.sh
```

یا یک backup مشخص:

```bash
RESTORE_DRILL_BACKUP_DIR=/opt/cloud-office/backups/20261007T020000Z \
./ops/backup/restore-drill.sh
```

پورت‌های پیش‌فرض drill با staging اصلی تداخل ندارند:

```env
RESTORE_DRILL_PROJECT=cloud-office-staging-drill
RESTORE_DRILL_BACKEND_PORT=18000
RESTORE_DRILL_MINIO_API_PORT=19000
RESTORE_DRILL_MINIO_CONSOLE_PORT=19001
```

فعال‌کردن اجرای هفتگی روی staging VM:

```bash
sudo cp ops/backup/cloud-office-restore-drill.service /etc/systemd/system/
sudo cp ops/backup/cloud-office-restore-drill.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cloud-office-restore-drill.timer
systemctl list-timers cloud-office-restore-drill.timer
```

گزارش و خطا:

```bash
journalctl -u cloud-office-restore-drill.service -n 200 --no-pager
ls -lt backups/restore-drills/
```

در production، failure این timer باید به Alertmanager/Slack/Telegram وصل شود؛ مثلاً با یک health metric یا systemd-exporter. موفقیت فقط وقتی ثبت شود که restore و smoke test کامل باشند، نه صرفاً وقتی containerها بالا آمدند.

### ارسال نتیجه به Telegram و Slack

`restore-drill.sh` در پایان اجرا، به‌صورت مستقیم نتیجه `PASSED` یا `FAILED` را ارسال می‌کند. از همان متغیرهای alerting پروژه استفاده می‌شود:

```env
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=-1001234567890
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
SLACK_CHANNEL=alerts
```

اگر Telegram credentials تنظیم شده باشد، پیام از Bot API ارسال می‌شود. اگر Slack webhook تنظیم شده باشد، پیام JSON به webhook می‌رود. هر دو را می‌توان هم‌زمان فعال کرد. خطای notification باعث پنهان‌شدن نتیجه drill نمی‌شود؛ exit code اصلی و report محلی حفظ می‌شوند.

در production، token و webhook را در secret manager یا `EnvironmentFile` خارج از Git قرار دهید. ابتدا با channel آزمایشی یک drill موفق و یک drill عمداً ناموفق را تست کنید. پیام باید شامل status، project و مسیر report باشد. برای جلوگیری از افشای اطلاعات، script محتوای backup و secretها را به notification ارسال نمی‌کند.

این drill نیازمند Docker واقعی، backup معتبر و منابع staging است. در sandbox بدون Docker فقط syntax آن قابل بررسی است.

برای سناریوی ازبین‌رفتن کامل VM، ابتدا VM جدید بسازید، repository را clone کنید، secretها را از secret manager بازیابی کنید، Compose را بالا بیاورید، database/object backup را restore کنید و DNS/traffic را پس از smoke test تغییر دهید.

## امنیت و نگهداری

- backup database و objectها را encrypt at rest و در انتقال کنید.
- backup credential را read/write محدود به bucket backup کنید.
- bucket backup را public نکنید.
- از password یا AI key در manifest و log جلوگیری کنید.
- backup محلی روی همان VM به‌تنهایی Disaster Recovery نیست.
- برای ransomware، immutable/retention lock و یک حساب جدا استفاده کنید.
- retention را طبق نیاز قانونی و کسب‌وکار تعیین کنید؛ مقدار ۱۴ روز فقط پیش‌فرض تستی است.
- before/after restore، migration version و application version را ثبت کنید.
