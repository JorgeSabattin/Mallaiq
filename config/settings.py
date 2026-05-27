"""
settings.py — Configuración Django
Malla Stress SaaS · Multi-universidad
"""
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Seguridad ──────────────────────────────────────────────────────
SECRET_KEY = config("SECRET_KEY", default="cambia-esto-en-produccion-unab2026")
DEBUG      = config("DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")

# ── Apps ───────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Apps propias
    "accounts",    # usuarios, organizaciones (universidades)
    "malla",       # carga de Excel y generación de dashboard
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # ← estáticos en producción
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

WSGI_APPLICATION = "config.wsgi.application"

# ── Base de datos ──────────────────────────────────────────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        # Para producción con PostgreSQL:
        # "ENGINE": "django.db.backends.postgresql",
        # "NAME":     config("DB_NAME"),
        # "USER":     config("DB_USER"),
        # "PASSWORD": config("DB_PASSWORD"),
        # "HOST":     config("DB_HOST", default="localhost"),
        # "PORT":     config("DB_PORT", default="5432"),
    }
}

# ── Auth ───────────────────────────────────────────────────────────
AUTH_USER_MODEL          = "accounts.User"
LOGIN_URL                = "/accounts/login/"
LOGIN_REDIRECT_URL       = "/dashboard/"
LOGOUT_REDIRECT_URL      = "/accounts/login/"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

# ── Internacionalización ───────────────────────────────────────────
LANGUAGE_CODE = "es-cl"
TIME_ZONE     = "America/Santiago"
USE_I18N      = True
USE_TZ        = True

# ── Archivos estáticos y media ─────────────────────────────────────
STATIC_URL   = "/static/"
STATIC_ROOT  = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL  = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ── Upload límites ─────────────────────────────────────────────────
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024   # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── Seguridad producción (activar cuando DEBUG=False) ──────────────
if not DEBUG:
    SECURE_HSTS_SECONDS        = 31536000
    SECURE_SSL_REDIRECT        = True
    SESSION_COOKIE_SECURE      = True
    CSRF_COOKIE_SECURE         = True
    SECURE_BROWSER_XSS_FILTER  = True
    X_FRAME_OPTIONS            = "DENY"
