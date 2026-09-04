"""
Django settings for config project.
"""

from pathlib import Path
import os

from dotenv import load_dotenv


# ==========================================================
# BASE DIRECTORY / ENVIRONMENT
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    BASE_DIR / ".env"
)


# ==========================================================
# SECURITY
# ==========================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY"
)

if not SECRET_KEY:
    raise RuntimeError(
        (
            "SECRET_KEY is missing. "
            "Add SECRET_KEY to the project's .env file."
        )
    )


DEBUG = (
    os.getenv(
        "DEBUG",
        "True",
    ).lower()
    in {
        "1",
        "true",
        "yes",
        "on",
    }
)


ALLOWED_HOSTS = []


# ==========================================================
# APPLICATIONS
# ==========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",

    "accounts",
    "home",
    "analytics",
    "publications",
    "notifications",
    "workflow",
]


# ==========================================================
# MIDDLEWARE
# ==========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"


# ==========================================================
# TEMPLATES
# ==========================================================

TEMPLATES = [
    {
        "BACKEND": (
            "django.template.backends.django.DjangoTemplates"
        ),
        "DIRS": [
            BASE_DIR / "templates"
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                (
                    "django.template.context_processors."
                    "request"
                ),
                (
                    "django.contrib.auth.context_processors."
                    "auth"
                ),
                (
                    "django.contrib.messages."
                    "context_processors.messages"
                ),
                (
                    "notifications.context_processors."
                    "notification_context"
                ),
            ],
        },
    },
]


WSGI_APPLICATION = "config.wsgi.application"


# ==========================================================
# DATABASE
# ==========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv(
            "DB_NAME"
        ),
        "USER": os.getenv(
            "DB_USER"
        ),
        "PASSWORD": os.getenv(
            "DB_PASSWORD"
        ),
        "HOST": os.getenv(
            "DB_HOST"
        ),
        "PORT": os.getenv(
            "DB_PORT"
        ),
    }
}


# ==========================================================
# PASSWORD VALIDATION
# ==========================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ==========================================================
# INTERNATIONALIZATION
# ==========================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Manila"

USE_I18N = True

USE_TZ = True


# ==========================================================
# STATIC / MEDIA
# ==========================================================

STATIC_URL = "static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = (
    BASE_DIR / "staticfiles"
)


MEDIA_URL = "/media/"

MEDIA_ROOT = (
    BASE_DIR / "media"
)


# ==========================================================
# ARTICLE UPLOAD SECURITY
# ==========================================================

ARTICLE_IMAGE_MAX_SIZE = (
    25 * 1024 * 1024
)

ARTICLE_IMAGE_MAX_PIXELS = (
    60_000_000
)


ARTICLE_ALLOWED_IMAGE_EXTENSIONS = [
    "jpg",
    "jpeg",
    "png",
    "webp",
]


ARTICLE_ALLOWED_IMAGE_FORMATS = [
    "JPEG",
    "PNG",
    "WEBP",
]


ARTICLE_MAX_ATTACHMENTS = 15


# Files above 2 MB are written to a
# temporary file rather than being kept
# entirely in memory during upload.
FILE_UPLOAD_MAX_MEMORY_SIZE = (
    2 * 1024 * 1024
)

DIGITAL_PUBLICATION_PDF_MAX_SIZE = (
    300 * 1024 * 1024
)

# ==========================================================
# DJANGO REST FRAMEWORK
# ==========================================================

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        (
            "rest_framework.authentication."
            "SessionAuthentication"
        ),
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        (
            "rest_framework.permissions."
            "IsAuthenticated"
        ),
    ],
}


# ==========================================================
# CUSTOM USER
# ==========================================================

AUTH_USER_MODEL = "accounts.User"


# ==========================================================
# EMAIL
# ==========================================================

MAILERS = {
    "default": {
        "BACKEND": (
            "django.core.mail.backends.console."
            "EmailBackend"
        ),
    },
}


# ==========================================================
# AUTH REDIRECTS
# ==========================================================

LOGIN_URL = "/login/"

LOGIN_REDIRECT_URL = (
    "/dashboard/"
)

LOGOUT_REDIRECT_URL = "/"