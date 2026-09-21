"""Offline test settings. Never load .env, remote databases, media or email."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = "local-tests-only-not-a-deployment-secret"
DEBUG = True
USE_TZ = True
TIME_ZONE = "Asia/Manila"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "accounts", "home", "analytics", "publications", "notifications",
    "workflow", "audit.apps.AuditConfig",
]
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["accounts.backends.VerifiedEmailModelBackend"]
ROOT_URLCONF = "config.urls"
MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
]
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates",
              "DIRS": [BASE_DIR / "templates"], "APP_DIRS": True,
              "OPTIONS": {"context_processors": [
                  "django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages",
                  "notifications.context_processors.notification_context",
              ]}}]
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / ".test-media"
STORAGES = {"default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
