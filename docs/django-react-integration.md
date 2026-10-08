# اتصال Django REST Framework و React Router در Cloud Office

این سند یک اسکلت آماده برای اتصال فرانت‌اند فعلی Cloud Office به Django REST Framework است. نمونه‌ها برای توسعه‌ی محلی نوشته شده‌اند و برای Production بخش‌های امنیتی لازم را هم مشخص می‌کنند.

---

## ۱. ساختار پیشنهادی نهایی

```text
cloud-office/
├── backend/
│   ├── manage.py
│   ├── .env.example
│   ├── requirements.txt
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py
│   │   ├── urls.py
│   │   ├── asgi.py
│   │   └── wsgi.py
│   ├── accounts/
│   ├── files/
│   ├── sharing/
│   └── activity/
└── src/
    ├── api/
    │   ├── client.ts
    │   ├── auth.ts
    │   └── files.ts
    ├── auth/
    │   ├── AuthProvider.tsx
    │   └── ProtectedRoute.tsx
    ├── components/
    │   ├── AppShell.tsx
    │   └── LoadingState.tsx
    ├── layouts/
    │   └── DashboardLayout.tsx
    ├── pages/
    │   ├── LoginPage.tsx
    │   ├── DashboardPage.tsx
    │   ├── FilesPage.tsx
    │   ├── SharedPage.tsx
    │   ├── MailPage.tsx
    │   ├── ActivityPage.tsx
    │   └── NotFoundPage.tsx
    ├── routes/
    │   └── AppRouter.tsx
    ├── types/
    │   └── api.ts
    ├── App.tsx
    └── main.tsx
```

اصل مهم: فایل فعلی `src/main.tsx` نباید محل نگهداری همه‌ی صفحات و داده‌های mock باقی بماند. `main.tsx` فقط باید providerها و router را mount کند.

---

# بخش Django

## ۲. نصب Backend

```bash
mkdir backend
cd backend
python3 -m venv .venv
source .venv/bin/activate

pip install Django djangorestframework \
  djangorestframework-simplejwt \
  django-cors-headers \
  django-filter \
  psycopg[binary] \
  python-dotenv

django-admin startproject config .
python manage.py startapp accounts
python manage.py startapp files
python manage.py startapp sharing
python manage.py startapp activity
```

## ۳. `requirements.txt`

```txt
Django>=5.1,<6.0
djangorestframework>=3.15,<4.0
djangorestframework-simplejwt>=5.3,<6.0
django-cors-headers>=4.4,<5.0
django-filter>=24.3,<25.0
psycopg[binary]>=3.2,<4.0
python-dotenv>=1.0,<2.0
```

## ۴. `.env.example`

```env
DJANGO_DEBUG=1
DJANGO_SECRET_KEY=replace-this-in-local-development
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_NAME=cloud_office
DATABASE_USER=cloud_office
DATABASE_PASSWORD=change-me
DATABASE_HOST=127.0.0.1
DATABASE_PORT=5432

FRONTEND_URL=http://localhost:5173
JWT_COOKIE_SECURE=0
CSRF_COOKIE_SECURE=0
```

در Production، `DJANGO_SECRET_KEY` را در secret manager قرار دهید و در Git commit نکنید.

---

## ۵. فایل کامل `backend/config/settings.py`

```python
from pathlib import Path
import os
from datetime import timedelta
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "unsafe-local-only-key")
DEBUG = env_bool("DJANGO_DEBUG", True)

ALLOWED_HOSTS = env_list(
    "DJANGO_ALLOWED_HOSTS",
    "localhost,127.0.0.1",
)

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party
    "corsheaders",
    "django_filters",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",

    # Local apps
    "accounts",
    "files",
    "sharing",
    "activity",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DATABASE_NAME", "cloud_office"),
        "USER": os.getenv("DATABASE_USER", "cloud_office"),
        "PASSWORD": os.getenv("DATABASE_PASSWORD", ""),
        "HOST": os.getenv("DATABASE_HOST", "127.0.0.1"),
        "PORT": os.getenv("DATABASE_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "connect_timeout": 5,
        },
    }
}

# اگر PostgreSQL هنوز آماده نیست، فقط در توسعه می‌توان موقتاً SQLite داشت.
# این block برای Production استفاده نشود.
if env_bool("USE_SQLITE", False):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "fa-ir"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# بعداً می‌توان آن را به مدل سفارشی accounts.User تغییر داد.
# این خط باید قبل از اولین migration مدل User اضافه شود.
# AUTH_USER_MODEL = "accounts.User"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ),
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "EXCEPTION_HANDLER": "config.api.custom_exception_handler",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# برای توسعه می‌توان localhost فرانت‌اند را مجاز کرد.
CORS_ALLOWED_ORIGINS = env_list(
    "FRONTEND_URL",
    "http://localhost:5173",
)
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS

# کوکی refresh در این نمونه در محیط توسعه ساده نگه داشته شده است.
# در Production: Secure=True و HTTPS اجباری است.
JWT_COOKIE_SECURE = env_bool("JWT_COOKIE_SECURE", not DEBUG)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
else:
    SECURE_SSL_REDIRECT = False

# در صورت استفاده از reverse proxy، این مقدار را مطابق زیرساخت تنظیم کنید.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

### نکته مهم درباره `AUTH_USER_MODEL`

اگر مدل User سفارشی می‌خواهید، باید `AUTH_USER_MODEL = "accounts.User"` را **قبل از اولین migration** فعال کنید. تغییر آن بعد از ایجاد migrationهای auth پرهزینه است.

---

## ۶. مسیرهای Django در `backend/config/urls.py`

```python
from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import LoginView, LogoutView, MeView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", LoginView.as_view(), name="auth-login"),
    path("api/auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),
    path("api/auth/logout/", LogoutView.as_view(), name="auth-logout"),
    path("api/auth/me/", MeView.as_view(), name="auth-me"),
    path("api/files/", include("files.urls")),
    path("api/sharing/", include("sharing.urls")),
    path("api/activity/", include("activity.urls")),
]
```

## ۷. API احراز هویت آماده

### `backend/accounts/views.py`

```python
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        response = Response({"access": data["access"]})
        response.set_cookie(
            "refresh_token",
            data["refresh"],
            httponly=True,
            secure=False,  # در Production برابر True شود.
            samesite="Lax",
            max_age=7 * 24 * 60 * 60,
        )
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.COOKIES.get("refresh_token")
        if token:
            try:
                RefreshToken(token).blacklist()
            except Exception:
                pass
        response = Response(status=status.HTTP_204_NO_CONTENT)
        response.delete_cookie("refresh_token")
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            "id": request.user.id,
            "username": request.user.get_username(),
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
        })
```

برای refresh در معماری امن، endpoint refresh باید cookie را بخواند و access token جدید برگرداند. در شروع می‌توان از `TokenRefreshView` استاندارد استفاده کرد و بعد آن را با view سفارشی جایگزین کرد.

---

# بخش React/Vite

## ۸. نصب Router

از ریشه‌ی فرانت‌اند:

```bash
pnpm add react-router-dom
```

## ۹. متغیر محیطی

فایل `.env.local`:

```env
VITE_API_URL=http://localhost:8000/api
```

در Production بهتر است frontend و backend یک origin داشته باشند و مقدار `VITE_API_URL=/api` باشد.

---

## ۱۰. typeهای API در `src/types/api.ts`

```typescript
export type User = {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
};

export type AuthResponse = {
  access: string;
};

export type FileItem = {
  id: number;
  name: string;
  type: "folder" | "pdf" | "sheet" | "doc";
  size: string;
  updated: string;
  owner: string;
  color: string;
};
```

## ۱۱. API client در `src/api/client.ts`

```typescript
const API_URL = import.meta.env.VITE_API_URL ?? "/api";

let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);

  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  if (response.status === 401) {
    setAccessToken(null);
    throw new Error("نشست شما منقضی شده است");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const message = payload?.detail ?? "خطایی در ارتباط با سرور رخ داد";
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}
```

## ۱۲. API احراز هویت در `src/api/auth.ts`

```typescript
import { apiFetch, setAccessToken } from "./client";
import type { AuthResponse, User } from "../types/api";

export async function login(username: string, password: string) {
  const result = await apiFetch<AuthResponse>("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  setAccessToken(result.access);
  return result;
}

export async function refreshAccessToken() {
  const result = await apiFetch<AuthResponse>("/auth/refresh/", {
    method: "POST",
  });
  setAccessToken(result.access);
  return result;
}

export async function getMe() {
  return apiFetch<User>("/auth/me/");
}

export async function logout() {
  await apiFetch<void>("/auth/logout/", { method: "POST" });
  setAccessToken(null);
}
```

## ۱۳. AuthProvider در `src/auth/AuthProvider.tsx`

```tsx
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getMe, login as loginRequest, logout as logoutRequest, refreshAccessToken } from "../api/auth";
import type { User } from "../types/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    refreshAccessToken()
      .then(() => getMe())
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  async function login(username: string, password: string) {
    await loginRequest(username, password);
    setUser(await getMe());
  }

  async function logout() {
    await logoutRequest();
    setUser(null);
  }

  const value = useMemo(
    () => ({ user, loading, login, logout }),
    [user, loading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth باید داخل AuthProvider استفاده شود");
  return value;
}
```

نکته امنیتی: access token فقط در memory نگه داشته شده و refresh token در cookie `HttpOnly` است؛ بنابراین refresh token در `localStorage` ذخیره نمی‌شود.

## ۱۴. ProtectedRoute در `src/auth/ProtectedRoute.tsx`

```tsx
import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "./AuthProvider";

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="loading-screen">در حال بررسی نشست...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <Outlet />;
}
```

## ۱۵. Layout جدید در `src/layouts/DashboardLayout.tsx`

```tsx
import { Outlet } from "react-router-dom";
import { AppShell } from "../components/AppShell";

export function DashboardLayout() {
  return (
    <AppShell>
      <Outlet />
    </AppShell>
  );
}
```

محتوای فعلی sidebar و topbar را از `main.tsx` به `AppShell.tsx` منتقل کنید. خود shell باید فقط `children` یا `<Outlet />` را نمایش دهد و منطق هر صفحه را نداند.

## ۱۶. Router در `src/routes/AppRouter.tsx`

```tsx
import { createBrowserRouter, Navigate } from "react-router-dom";
import { ProtectedRoute } from "../auth/ProtectedRoute";
import { DashboardLayout } from "../layouts/DashboardLayout";
import { LoginPage } from "../pages/LoginPage";
import { DashboardPage } from "../pages/DashboardPage";
import { FilesPage } from "../pages/FilesPage";
import { SharedPage } from "../pages/SharedPage";
import { MailPage } from "../pages/MailPage";
import { ActivityPage } from "../pages/ActivityPage";
import { NotFoundPage } from "../pages/NotFoundPage";

export const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <DashboardLayout />,
        children: [
          { path: "/", element: <DashboardPage /> },
          { path: "/files", element: <FilesPage /> },
          { path: "/shared", element: <SharedPage /> },
          { path: "/mail", element: <MailPage /> },
          { path: "/activity", element: <ActivityPage /> },
        ],
      },
    ],
  },
  { path: "*", element: <NotFoundPage /> },
]);
```

## ۱۷. `src/App.tsx` و `src/main.tsx`

```tsx
// src/App.tsx
import { RouterProvider } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import { router } from "./routes/AppRouter";

export function App() {
  return (
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  );
}
```

```tsx
// src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

## ۱۸. نمونه LoginPage

```tsx
import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setSaving(true);
    try {
      await login(username, password);
      const from = (location.state as { from?: Location })?.from?.pathname ?? "/";
      navigate(from, { replace: true });
    } catch {
      setError("نام کاربری یا رمز عبور صحیح نیست");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="login-page">
      <form className="login-card glass" onSubmit={handleSubmit}>
        <h1>ورود به دفتر ابری</h1>
        {error && <p role="alert" className="form-error">{error}</p>}
        <label>نام کاربری<input value={username} onChange={(e) => setUsername(e.target.value)} required /></label>
        <label>رمز عبور<input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>
        <button className="primary" disabled={saving}>{saving ? "در حال ورود..." : "ورود"}</button>
      </form>
    </main>
  );
}
```

---

# ۱۹. جابه‌جایی داده‌های mock به API

در ابتدا `src/api/files.ts` را اضافه کنید:

```typescript
import { apiFetch } from "./client";
import type { FileItem } from "../types/api";

type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export async function listFiles(query = "") {
  const suffix = query ? `?search=${encodeURIComponent(query)}` : "";
  return apiFetch<Paginated<FileItem>>(`/files/${suffix}`);
}
```

سپس در `FilesPage.tsx` از `useEffect` یا React Query استفاده کنید:

```tsx
const [files, setFiles] = useState<FileItem[]>([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState("");

useEffect(() => {
  listFiles(search)
    .then((response) => setFiles(response.results))
    .catch(() => setError("دریافت فایل‌ها با خطا مواجه شد"))
    .finally(() => setLoading(false));
}, [search]);
```

تا وقتی API آماده نشده، می‌توان یک `mockFiles.ts` نگه داشت و فقط implementation تابع `listFiles` را عوض کرد؛ کامپوننت‌های UI نباید بدانند داده از mock می‌آید یا Django.

---

# ۲۰. ترتیب اجرای migration و راه‌اندازی

```bash
cd backend
source .venv/bin/activate
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

فرانت‌اند:

```bash
cd ..
pnpm install
pnpm dev
```

آدرس‌ها:

```text
React:  http://localhost:5173
Django: http://localhost:8000
Admin:  http://localhost:8000/admin/
API:    http://localhost:8000/api/
```

---

# ۲۱. چک‌لیست امنیتی قبل از Production

- `DEBUG=False`
- secret key خارج از Git
- HTTPS اجباری
- refresh token در HttpOnly + Secure cookie
- CORS فقط برای originهای واقعی
- rate limit روی login
- قفل حساب پس از تلاش ناموفق مکرر
- کنترل permission در queryset و object-level permission
- محدودیت حجم و MIME type فایل
- نام‌گذاری امن فایل و جلوگیری از path traversal
- اسکن ویروس قبل از قابل‌دسترسی شدن فایل
- ثبت AuditLog برای login، download، share، edit و delete
- عدم نمایش خطاهای خام backend به کاربر

# ۲۲. مسیر مهاجرت از نسخه فعلی

1. ابتدا `src/main.tsx` را بدون تغییر ظاهر، به `App.tsx`، صفحات و `AppShell` تقسیم کنید.
2. React Router را اضافه و routeهای فعلی را مطابق `src/routes/AppRouter.tsx` نگه دارید.
3. `AuthProvider` و LoginPage را اضافه کنید، ولی فایل‌های mock را موقتاً نگه دارید.
4. Django را با SQLite بالا بیاورید تا قرارداد API تثبیت شود؛ سپس PostgreSQL را فعال کنید.
5. بعد از موفقیت login، `listFiles` را به endpoint واقعی وصل کنید.
6. upload، sharing و activity را به‌صورت مرحله‌ای جایگزین mock کنید.
7. در پایان CORS توسعه را حذف و frontend/backend را پشت یک origin یا reverse proxy قرار دهید.
