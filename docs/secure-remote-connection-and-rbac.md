# Secure Remote Connection و RBAC

## 1. معماری اتصال امن

جریان اتصال در backend در اپ `support` پیاده شده است:

- `backend/support/remote_models.py`: مدل `RemoteSession` با مالک (`requester`)، کارشناس اختصاص‌یافته (`agent`)، کد هش‌شده، وضعیت، زمان انقضا و زمان رضایت.
- `backend/support/remote_views.py`: APIهای ایجاد، join، مشاهده، consent و پایان جلسه.
- `backend/support/remote_serializers.py`: خروجی وضعیت نشست و نام طرفین.
- `backend/support/consumers.py`: کانال WebSocket برای سیگنالینگ WebRTC و چت.
- `backend/support/ws_auth.py`: اعتبارسنجی JWT در subprotocol وب‌سوکت.
- `src/pages/RemoteSupportPage.tsx`: جریان UI ایجاد/ورود/رضایت.
- `src/pages/VideoConferencePage.tsx` و `src/hooks/useRemoteConference.ts`: اتاق ویدیو، رسانه و سیگنالینگ سمت کلاینت.

### چرخه وضعیت

```text
pending --(کارشناس مجاز join می‌کند + مالک consent می‌دهد)--> active
pending --(انقضا)--> expired
active  --(مالک یا کارشناس اختصاص‌یافته پایان می‌دهد)--> ended
```

کد خام فقط هنگام ایجاد نشست در پاسخ API برگردانده می‌شود؛ در دیتابیس فقط `SHA-256(code)` ذخیره می‌شود. عمر پیش‌فرض کد ۱۰ دقیقه است.

## 2. API پیاده‌سازی‌شده

### ایجاد نشست

```http
POST /api/support/remote-sessions/
Authorization: Bearer <access-token>
Content-Type: application/json

{"conversation_id": null, "mode": "screen_share"}
```

پاسخ شامل `id`، `status: "pending"`، `code`، `expires_at` و `consent_required: true` است. فقط کاربر احراز هویت‌شده می‌تواند نشست را به‌عنوان مالک ایجاد کند.

### ورود کارشناس با کد

```http
POST /api/support/remote-sessions/join/
Authorization: Bearer <access-token>
Content-Type: application/json

{"code": "AB12CD34"}
```

این endpoint ابتدا `CanReplySupport` را بررسی می‌کند، سپس کد را hash کرده و نشست pending و معتبر را پیدا می‌کند. کاربر در `session.agent` ثبت می‌شود؛ تا زمان رضایت مالک، وضعیت active نمی‌شود.

### مشاهده نشست

```http
GET /api/support/remote-sessions/<id>/
Authorization: Bearer <access-token>
```

بعد از اصلاح امنیتی، فقط `requester` یا `agent` همان نشست مجاز به مشاهده آن هستند؛ داشتن مجوز عمومی پشتیبانی برای خواندن نشست فعال کافی نیست.

### ثبت رضایت مالک

```http
POST /api/support/remote-sessions/<id>/consent/
Authorization: Bearer <owner-access-token>
```

فقط مالک سیستم می‌تواند consent کند. نشست باید pending، منقضی‌نشده و دارای agent باشد. سپس `status=active`، `consented_at` و `started_at` ثبت می‌شوند.

### پایان نشست

```http
POST /api/support/remote-sessions/<id>/end/
Authorization: Bearer <participant-access-token>
```

فقط مالک یا کارشناس اختصاص‌یافته می‌تواند نشست را پایان دهد؛ زمان `ended_at` و وضعیت ended ثبت می‌شود.

## 3. WebSocket و WebRTC

مسیر:

```text
/ws/remote/<session_id>/
```

کلاینت JWT را در subprotocol می‌فرستد:

```text
["access_token", "<jwt>"]
```

`AccessTokenSubprotocolMiddleware` توکن را decode می‌کند و کاربر را به scope اضافه می‌کند. `RemoteConferenceConsumer` سپس فقط نشست active را می‌پذیرد و فقط مالک یا agent اختصاص‌یافته را authorize می‌کند.

Envelope پیام‌ها یکسان است:

```json
{
  "type": "webrtc.offer | webrtc.answer | webrtc.ice-candidate | chat.message",
  "payload": {},
  "peer_id": 12
}
```

پیام‌های `webrtc.*` از فرستنده به خودش بازپخش نمی‌شوند. پیام چت با محدودیت ۵۰۰۰ نویسه در conversation ذخیره و به گروه ارسال می‌شود. برای نشست مستقل که `conversation_id` ندارد، backend به‌صورت خودکار conversation با موضوع «جلسه اتصال امن» می‌سازد تا پیام‌ها بعد از refresh هم در backend باقی بمانند.

## 4. ماتریس RBAC

### نقش‌ها و مجوزهای پایه

| مجوز | owner | admin | support | auditor | member |
| --- | ---: | ---: | ---: | ---: | ---: |
| `manage_users` | ✓ | ✓ | — | — | — |
| `manage_roles` | ✓ | — | — | — | — |
| `manage_support` | ✓ | ✓ | — | — | — |
| `reply_support` | explicit grant | explicit grant | explicit grant | — | — |
| `view_admin` | ✓ | ✓ | — | — | — |
| `view_files` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `edit_files` | ✓ | ✓ | — | — | ✓ |
| `view_mail` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `view_activity` | ✓ | ✓ | — | ✓ | ✓ |
| `view_remote` | ✓ | ✓ | ✓ | — | ✓ |

`reply_support` عمداً استثناست: حتی اگر role definition مقدار `reply_support=true` داشته باشد، backend آن را حذف می‌کند و فقط وجود رکورد `SupportAgentPermission(can_reply=True)` آن را فعال می‌کند.

## 5. سلسله‌مراتب محاسبه مجوز

ترتیب تصمیم‌گیری در `backend/support/permissions.py`:

1. کاربر احراز هویت نشده: هیچ role یا permission ندارد.
2. `is_superuser`: نقش مؤثر `owner` و مجوزهای مدیریتی کامل؛ پاسخ‌گویی پشتیبانی همچنان به grant صریح وابسته است.
3. نقش‌های چندگانه از `UserRole` خوانده می‌شوند.
4. اگر `UserRole` وجود نداشته باشد، سیستم legacy از `AccessRole` استفاده می‌کند.
5. اگر هیچ رکورد نقشی وجود نداشته باشد، `is_staff` به `admin` و سایر کاربران به `member` fallback می‌شوند.
6. `role_for()` برای نقش اصلی از اولویت زیر استفاده می‌کند:

```text
owner > admin > support > auditor > member
```

7. `merged_permissions()` مجوزهای تمام `RoleDefinition`های کاربر را union می‌کند؛ مقدار true در هر نقش کافی است.
8. `reply_support` از union نقش‌ها حذف و فقط از `SupportAgentPermission` اضافه می‌شود.
9. permission classها روی این نتیجه اعمال می‌شوند:
   - `CanManageAccess`: `manage_users` یا نقش owner/admin
   - `CanViewAdmin`: `view_admin` یا نقش owner/admin
   - `CanReplySupport`: فقط `SupportAgentPermission.can_reply=True`

## 6. تغییرات امنیتی کلیدی

- envelope سیگنالینگ WebSocket اصلاح شد تا `type` و `payload` تخت نشوند و SDP/ICE/chat خراب نشود.
- کارشناس پشتیبانی عمومی دیگر نمی‌تواند نشست active متعلق به کارشناس دیگری را ببیند یا terminate کند.
- فعال‌سازی رسانه توسط answerer با renegotiation به offerer اطلاع داده می‌شود.
- role اصلی و `UserRole` در endpoint تغییر نقش هم‌زمان می‌شوند.
- خطای lookup نشست، نشست قبلی را در state نگه نمی‌دارد.
- تست regression برای جلوگیری از دسترسی کارشناس اختصاص‌نیافته اضافه شده است.

## 7. تست‌ها

```bash
cd backend
python manage.py test accounts support files -v 1
```

نتیجه آخرین اجرا: **۱۰ تست موفق**.

## 8. حساب توسعه

در دیتابیس SQLite محلی این محیط حساب زیر ساخته/به‌روزرسانی شده است:

```text
username: admin
password: admin
role: owner / superuser
```

این credential در source code یا repository ذخیره نشده و برای production مناسب نیست؛ قبل از استقرار باید حذف یا با رمز قوی جایگزین شود.


## 9. ساختار و طراحی ویدیوکنفرانس

صفحه `src/pages/VideoConferencePage.tsx` به‌عنوان لایهٔ نمایش و orchestration عمل می‌کند. ابتدا شناسهٔ نشست را از query string می‌خواند، وضعیت active را از API می‌گیرد، سپس فقط برای نشست فعال hook کنفرانس را mount می‌کند. این ترتیب باعث می‌شود WebSocket قبل از ثبت رضایت مالک باز نشود.

`src/hooks/useRemoteConference.ts` لایهٔ رفتار زنده است: ساخت `RTCPeerConnection`، صف‌کردن ICE candidateها، ارسال offer/answer، دریافت trackهای راه‌دور، اتصال local stream به video element، کنترل دوربین/اشتراک صفحه/میکروفون، cleanup و مدیریت چت. صفحه فقط intentهای کاربر را به hook می‌دهد و از جزئیات WebRTC جدا می‌ماند.

در UI دسکتاپ، stage ویدیو بخش غالب است و side panel سه سطح دارد: وضعیت امنیت، شرکت‌کنندگان و چت. local preview در گوشهٔ stage به‌صورت picture-in-picture قرار گرفته و media dock زیر stage باقی می‌ماند تا کنترل‌ها همیشه قابل مشاهده باشند.

### واکنش‌گرایی

فایل `src/conference-responsive.css` breakpointهای مشخصی اضافه می‌کند:

| حالت | رفتار |
| --- | --- |
| دسکتاپ، ۱۱۰۰px به بالا | stage بزرگ در کنار side panel حدود ۳۱۸px |
| تبلت، ۷۶۰ تا ۱۰۹۹px | stage تمام‌عرض؛ کارت امنیت و شرکت‌کنندگان کنار هم؛ چت در ردیف کامل |
| موبایل، زیر ۷۶۰px | همه‌چیز عمودی؛ stage کوتاه‌تر؛ PIP کوچک‌تر؛ کنترل‌های رسانه در شبکهٔ ۲×۲ |
| موبایل باریک، زیر ۴۲۰px | کاهش بیشتر stage و PIP، شکستن امن نام‌ها و پیام‌های طولانی |
| موبایل افقی | stage و side panel در دو ستون باریک برای استفاده از ارتفاع کم |

برای جلوگیری از شکستن RTL از `min-width: 0`، `minmax(0, 1fr)`، `overflow-wrap:anywhere` و max-width پیام استفاده شده است. composer چت در موبایل تمام‌عرض است و دکمهٔ ارسال حداقل ۴۴px سطح لمس دارد. حالت `prefers-reduced-motion` نیز حفظ شده است.

### اعتبارسنجی responsive

ساخت TypeScript/Vite موفق است و route صفحه با HTTP 200 پاسخ می‌دهد. برای QA دیداری، این اندازه‌ها باید بررسی شوند: `1280×720` دسکتاپ، `768×1024` تبلت، `375×812` موبایل و `812×375` موبایل افقی. محدودیت‌های دوربین، میکروفون، screen capture و WebRTC همچنان به permission مرورگر و پشتیبانی دستگاه وابسته‌اند.

## 10. لاگ و مشاهده‌پذیری اتصال

برای تست و production diagnostics، `backend/support/consumers.py` رویدادهای زیر را با logger اختصاصی `support.consumers` ثبت می‌کند:

```text
webrtc.connected
webrtc.signal event=webrtc.offer|webrtc.answer|webrtc.ice-candidate
chat.message
webrtc.disconnected
webrtc.connect_denied
```

در لاگ فقط `session_id`، `user_id`، نوع رویداد، `message_id` و `close_code` ثبت می‌شود. access token، raw session code، SDP و متن پیام در log چاپ نمی‌شوند.

تنظیمات console logger در `backend/config/settings.py` قرار دارد و برای production بهتر است handler به سیستم مرکزی log با retention و redaction مناسب متصل شود.
