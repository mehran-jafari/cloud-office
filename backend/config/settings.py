from pathlib import Path
from datetime import timedelta
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

def env_bool(name, default=False):
    value = os.getenv(name)
    return default if value is None else value.lower() in {'1', 'true', 'yes', 'on'}

def env_list(name, default=''):
    return [item.strip() for item in os.getenv(name, default).split(',') if item.strip()]

def env_choice(name, default, allowed):
    value = os.getenv(name, default)
    return value if value in allowed else default

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'unsafe-local-development-secret-key')
DEBUG = env_bool('DJANGO_DEBUG', True)
ALLOWED_HOSTS = env_list('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1')
INSTALLED_APPS = ['daphne', 'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles', 'corsheaders', 'django_filters', 'channels', 'rest_framework', 'rest_framework_simplejwt.token_blacklist', 'accounts.apps.AccountsConfig', 'files', 'support', 'ai.apps.AiConfig', 'desk.apps.DeskConfig']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'whitenoise.middleware.WhiteNoiseMiddleware', 'corsheaders.middleware.CorsMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware', 'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware', 'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware', 'django.middleware.clickjacking.XFrameOptionsMiddleware', 'monitoring.observe_request']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [], 'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request', 'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'
# Use InMemoryChannelLayer for local/dev without Redis. Set REDIS_URL to enable Redis-backed channels.
_redis_url = os.getenv('REDIS_URL', '').strip()
if _redis_url:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {'hosts': [_redis_url]},
        }
    }
else:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }

if env_bool('USE_POSTGRES', False):
    DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': os.getenv('DATABASE_NAME', 'cloud_office'), 'USER': os.getenv('DATABASE_USER', 'cloud_office'), 'PASSWORD': os.getenv('DATABASE_PASSWORD', ''), 'HOST': os.getenv('DATABASE_HOST', '127.0.0.1'), 'PORT': os.getenv('DATABASE_PORT', '5432'), 'CONN_MAX_AGE': 60}}
else:
    DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LANGUAGE_CODE = 'fa-ir'
TIME_ZONE = 'Asia/Tehran'
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Object storage. Keep local filesystem storage for a zero-dependency dev run;
# set USE_S3=1 for MinIO, S3, or another S3-compatible provider.
# Static files are served by WhiteNoise (Daphne does not serve them).
USE_S3 = env_bool('USE_S3', False)
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage'},
}
if USE_S3:
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {
            'bucket_name': os.getenv('AWS_STORAGE_BUCKET_NAME', 'cloud-office'),
            'access_key': os.getenv('AWS_ACCESS_KEY_ID', ''),
            'secret_key': os.getenv('AWS_SECRET_ACCESS_KEY', ''),
            'endpoint_url': os.getenv('AWS_S3_ENDPOINT_URL', '').strip() or None,
            'region_name': os.getenv('AWS_S3_REGION_NAME', 'us-east-1'),
            'addressing_style': os.getenv('AWS_S3_ADDRESSING_STYLE', 'path'),
            'signature_version': os.getenv('AWS_S3_SIGNATURE_VERSION', 's3v4'),
            'default_acl': None,
            'file_overwrite': False,
            'querystring_auth': env_bool('AWS_QUERYSTRING_AUTH', True),
            'querystring_expire': int(os.getenv('AWS_QUERYSTRING_EXPIRE', '900')),
        },
    }

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 24,
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '30/min',
        'user': '120/min',
        'login': '8/min',
        'upload': '20/min',
        'ai': '15/min',
        'desk_connect': '10/min',
        'desk_lookup': '30/min',
        'support_msg': '20/min',
    },
}
SIMPLE_JWT = {'ACCESS_TOKEN_LIFETIME': timedelta(minutes=10), 'REFRESH_TOKEN_LIFETIME': timedelta(days=7), 'ROTATE_REFRESH_TOKENS': True, 'BLACKLIST_AFTER_ROTATION': True, 'UPDATE_LAST_LOGIN': True, 'AUTH_HEADER_TYPES': ('Bearer',)}
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {
        'support': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
        'accounts': {'handlers': ['console'], 'level': 'INFO', 'propagate': False},
    },
}
CORS_ALLOWED_ORIGINS = env_list('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://localhost:5173')
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = env_list('CSRF_TRUSTED_ORIGINS', ','.join(CORS_ALLOWED_ORIGINS))
CORS_PREFLIGHT_MAX_AGE = 600
CORS_ALLOW_PRIVATE_NETWORK = False

# OnlyOffice integration. APP_PUBLIC_URL must be reachable by Document Server in production.
ONLYOFFICE_URL = os.getenv('ONLYOFFICE_URL', 'http://localhost:8080')
APP_PUBLIC_URL = os.getenv('APP_PUBLIC_URL', '').rstrip('/')
ONLYOFFICE_CALLBACK_SECRET = os.getenv('ONLYOFFICE_CALLBACK_SECRET', 'unsafe-onlyoffice-callback-secret-change-me')
EDITOR_SIGNING_SALT = os.getenv('EDITOR_SIGNING_SALT', 'cloud-office-editor-v1')
EDITOR_URL_TTL_SECONDS = int(os.getenv('EDITOR_URL_TTL_SECONDS', '300'))
EDITOR_MAX_DOWNLOAD_BYTES = int(os.getenv('EDITOR_MAX_DOWNLOAD_BYTES', str(100 * 1024 * 1024)))
METRICS_TOKEN = os.getenv('METRICS_TOKEN', '')

# Refresh JWT is stored only in an HttpOnly cookie. Keep these configurable because
# cross-origin HTTPS deployments require Secure cookies while local HTTP does not.
REFRESH_COOKIE_NAME = 'refresh_token'
REFRESH_COOKIE_SECURE = env_bool('REFRESH_COOKIE_SECURE', not DEBUG)
REFRESH_COOKIE_SAMESITE = env_choice('REFRESH_COOKIE_SAMESITE', 'Lax', {'Lax', 'Strict', 'None'})
REFRESH_COOKIE_PATH = '/api/auth/'
CSRF_COOKIE_SECURE = env_bool('CSRF_COOKIE_SECURE', not DEBUG)
CSRF_COOKIE_SAMESITE = env_choice('CSRF_COOKIE_SAMESITE', 'Lax', {'Lax', 'Strict', 'None'})
SESSION_COOKIE_SECURE = env_bool('SESSION_COOKIE_SECURE', not DEBUG)
SESSION_COOKIE_SAMESITE = env_choice('SESSION_COOKIE_SAMESITE', 'Lax', {'Lax', 'Strict', 'None'})
# فقط وقتی پشت reverse proxy مورد اعتماد (nginx/Traefik/...) هستید فعال کنید؛
# در غیر این صورت کلاینت می‌تواند X-Forwarded-Proto را جعل کند.
if env_bool('TRUST_PROXY_SSL_HEADER', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = env_bool('USE_X_FORWARDED_HOST', False)
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', True)
    # healthcheck داخلی (HTTP ساده، بدون پروکسی) نباید به https ریدایرکت شود
    SECURE_REDIRECT_EXEMPT = [r'^api/health/$']
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'


# --- Production security gate ---
_unsafe_secrets = {
    'unsafe-local-development-secret-key',
    'replace-with-a-long-random-secret-for-production',
}
_unsafe_callback_secrets = {
    'unsafe-onlyoffice-callback-secret-change-me',
    'replace-with-a-long-random-callback-secret',
}
if not DEBUG:
    if SECRET_KEY in _unsafe_secrets or len(SECRET_KEY) < 40:
        raise RuntimeError(
            'DJANGO_SECRET_KEY must be set to a long random value when DEBUG=0.'
        )
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['*']:
        raise RuntimeError('DJANGO_ALLOWED_HOSTS must be set explicitly when DEBUG=0.')
    if ONLYOFFICE_CALLBACK_SECRET in _unsafe_callback_secrets or len(ONLYOFFICE_CALLBACK_SECRET) < 32:
        raise RuntimeError(
            'ONLYOFFICE_CALLBACK_SECRET must be set to a long random value (>=32 chars) when DEBUG=0.'
        )


# AI (OpenAI-compatible). Without AI_API_KEY, local fallback templates are used.
AI_API_KEY = os.getenv('AI_API_KEY', '') or os.getenv('OPENAI_API_KEY', '')
AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://api.openai.com/v1')
AI_CHAT_MODEL = os.getenv('AI_CHAT_MODEL', 'gpt-4o-mini')
AI_EMBED_MODEL = os.getenv('AI_EMBED_MODEL', 'text-embedding-3-small')
AI_STT_MODEL = os.getenv('AI_STT_MODEL', 'whisper-1')
# Support auto-reply runs inside the HTTP request, so keep its timeout short.
# آدرس عمومی برنامه برای نصب‌کننده Desk (مثلاً https://office.example.com). خالی = از درخواست تشخیص داده می‌شود.
PUBLIC_APP_URL = os.getenv('PUBLIC_APP_URL', '').strip()
SUPPORT_AI_TIMEOUT = int(os.getenv('SUPPORT_AI_TIMEOUT', '20'))

# OnlyOffice callback: hosts the Document Server may serve the saved file from.
# The host of ONLYOFFICE_URL is always allowed.
ONLYOFFICE_ALLOWED_HOSTS = env_list('ONLYOFFICE_ALLOWED_HOSTS', '')


# WebRTC ICE (STUN/TURN) — for production set TURN_URLS / TURN_USERNAME / TURN_PASSWORD
_ice = [
    {'urls': 'stun:stun.l.google.com:19302'},
    {'urls': 'stun:stun1.l.google.com:19302'},
]
_turn = os.getenv('TURN_URLS', '').strip()
if _turn:
    _entry = {'urls': [u.strip() for u in _turn.split(',') if u.strip()]}
    if os.getenv('TURN_USERNAME'):
        _entry['username'] = os.getenv('TURN_USERNAME')
        _entry['credential'] = os.getenv('TURN_PASSWORD', '')
    _ice.append(_entry)
WEBRTC_ICE_SERVERS = _ice


# --- Email (optional) ---
# For production set EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD.
# Without EMAIL_HOST, only in-app notifications are created.
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend' if DEBUG else 'django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST = os.getenv('EMAIL_HOST', '')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = env_bool('EMAIL_USE_TLS', True)
EMAIL_USE_SSL = env_bool('EMAIL_USE_SSL', False)
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'Cloud Office <noreply@cloud-office.local>')
# اگر True باشد همه اعلان‌ها ایمیل هم می‌فرستند (پیش‌فرض: فقط وقتی صریحاً درخواست شود)
NOTIFY_EMAIL_ON_ALL = env_bool('NOTIFY_EMAIL_ON_ALL', False)
