import os
from pathlib import Path
from urllib.parse import parse_qs, urlparse


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-change-me")
DEBUG = os.environ.get("DEBUG", "False").lower() in {"1", "true", "yes"}

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",")
    if origin.strip()
]

SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "False").lower() in {"1", "true", "yes"}
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if os.environ.get("SECURE_PROXY_SSL_HEADER", "False").lower() in {"1", "true", "yes"}
    else None
)
SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("SECURE_HSTS_INCLUDE_SUBDOMAINS", "False").lower() in {"1", "true", "yes"}
SECURE_HSTS_PRELOAD = os.environ.get("SECURE_HSTS_PRELOAD", "False").lower() in {"1", "true", "yes"}
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in {"1", "true", "yes"}
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() in {"1", "true", "yes"}

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "companies",
    "jobs",
    "profiles",
    "agents",
    "notifications",
    "matching",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "api.auth.ApiTokenMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "jobhunt.urls"

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

WSGI_APPLICATION = "jobhunt.wsgi.application"


def database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    engine = "django.db.backends.postgresql" if parsed.scheme.startswith("postgres") else "django.db.backends.sqlite3"
    if engine.endswith("sqlite3"):
        return {"ENGINE": engine, "NAME": parsed.path.lstrip("/") or BASE_DIR / "db.sqlite3"}
    config = {
        "ENGINE": engine,
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or "",
        "CONN_MAX_AGE": 60,
    }
    query = parse_qs(parsed.query)
    sslmode = os.environ.get("DATABASE_SSLMODE") or (query.get("sslmode", [None])[0])
    if not sslmode:
        local_hosts = {"localhost", "127.0.0.1", "db", "postgres"}
        sslmode = "disable" if (parsed.hostname or "").lower() in local_hosts else "require"
    if sslmode:
        config["OPTIONS"] = {"sslmode": sslmode}
    return config


DATABASES = {
    "default": database_from_url(os.environ["DATABASE_URL"])
    if os.environ.get("DATABASE_URL")
    else {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [path for path in [BASE_DIR / "static"] if path.exists()]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SCRAPER_USER_AGENT = os.environ.get(
    "SCRAPER_USER_AGENT",
    "CompanyJobScraper/1.0 (+https://github.com/self-hosted-job-scraper)",
)
SCRAPER_TIMEOUT_SECONDS = int(os.environ.get("SCRAPER_TIMEOUT_SECONDS", "20"))

JOB_SCOUT_REQUIRE_AUTH = os.environ.get("JOB_SCOUT_REQUIRE_AUTH", "False").lower() in {"1", "true", "yes"}
JOB_SCOUT_API_TOKEN = os.environ.get("JOB_SCOUT_API_TOKEN", "")

AGENT_EXECUTION_MODE = os.environ.get("AGENT_EXECUTION_MODE", "inline").strip().lower()
AGENT_QUEUE_BATCH_SIZE = int(os.environ.get("AGENT_QUEUE_BATCH_SIZE", "5"))

LANGSMITH_TRACING = os.environ.get("LANGSMITH_TRACING", "False").lower() in {"1", "true", "yes"}
LANGSMITH_PROJECT = os.environ.get("LANGSMITH_PROJECT", "job-scout-v3").strip()

EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "25"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "False").lower() in {"1", "true", "yes"}
EMAIL_USE_SSL = os.environ.get("EMAIL_USE_SSL", "False").lower() in {"1", "true", "yes"}
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Job Scout <job-scout@example.local>")
