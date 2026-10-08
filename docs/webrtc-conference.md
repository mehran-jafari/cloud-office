# WebRTC و ویدیوکنفرانس Remote Support

## معماری

React browser media → `RTCPeerConnection` → WebSocket signaling → Django Channels/Redis → peer browser.

Redis فقط signaling را fan-out می‌کند؛ صدا و تصویر از مسیر WebRTC عبور می‌کنند و نباید از Django relay شوند.

## جریان جلسه

1. کاربر از `/remote-support` یک session می‌سازد.
2. کارشناس مجاز با کد join می‌کند.
3. صاحب سیستم consent می‌کند؛ backend وضعیت را `active` می‌کند.
4. هر دو طرف به `wss://api.example.com/ws/remote/<id>/` وصل می‌شوند.
5. صاحب سیستم با `getDisplayMedia()` صفحه را share می‌کند.
6. هر طرف در صورت نیاز `getUserMedia()` دوربین و میکروفون را فعال می‌کند.
7. offer/answer/ICE از Channels عبور می‌کنند.
8. chat جلسه از همان WebSocket ارسال و در صورت وجود conversation در دیتابیس ذخیره می‌شود.
9. با پایان جلسه، WebSocket و trackهای media بسته می‌شوند.

## تنظیمات

```env
REDIS_URL=redis://127.0.0.1:6379/0
VITE_WS_URL=wss://api.example.com
VITE_ICE_SERVERS=[{"urls":"stun:stun.l.google.com:19302"},{"urls":"turn:turn.example.com","username":"...","credential":"..."}]
```

در production، TURN واقعی و HTTPS/WSS لازم است؛ STUN به‌تنهایی پشت NAT سخت کافی نیست. credentialهای TURN نباید دائمی یا در source control باشند؛ از credential کوتاه‌عمر استفاده کنید.

## پیام‌های signaling

```text
peer.joined
peer.left
webrtc.offer       { payload: RTCSessionDescriptionInit }
webrtc.answer      { payload: RTCSessionDescriptionInit }
webrtc.ice-candidate { payload: RTCIceCandidateInit }
chat.message       { payload: message }
chat.error
```

## نکات امنیتی

- فقط session فعال و participant مجاز اجازه‌ی handshake دارد.
- فقط صاحب سیستم screen share را با user gesture شروع می‌کند.
- browser permission را دور نزنید و کنترل مخفی اضافه نکنید.
- token را log نکنید؛ از subprotocol کوتاه‌عمر یا ticket یک‌بارمصرف استفاده کنید.
- Origin و session membership را در WebSocket بررسی کنید.
- برای پیام، connection و session rate limit بگذارید.
- پایان جلسه باید همه‌ی trackها و peer connection را stop کند.
- برای کنترل mouse/keyboard سیستم‌عامل، browser کافی نیست؛ Desktop Agent امضاشده با pairing و allow-list لازم است.

## تست

- دو browser context با دو کاربر متفاوت باز کنید.
- session را بسازید، join کنید و consent کنید.
- screen share را در مالک و camera/mic را در هر طرف فعال کنید.
- offer، answer و ICE را در هر دو طرف مشاهده کنید.
- پیام چت را بدون refresh بررسی کنید.
- TURN را با شبکه‌ی محدود تست کنید.
- با پایان جلسه، trackها و WebSocket را بررسی کنید.
