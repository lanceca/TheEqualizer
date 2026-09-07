"""
Django settings for config project.

Local development:
- Uses the existing MySQL/MariaDB settings when DATABASE_URL is not set.
- Uses local filesystem media when Supabase S3 variables are not set.
- Uses console email unless EMAIL_BACKEND is configured.

Production:
- Uses DATABASE_URL for PostgreSQL (Supabase).
- Uses WhiteNoise for static files.
- Uses Supabase Storage through its S3-compatible endpoint when configured.
- Uses Brevo's HTTPS transactional-email API for verification/password reset mail.
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


def env_bool(name, default=False):
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def env_list(name, default=""):
    value = os.getenv(name, default)

    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


# ==========================================================
# SECURITY
# ==========================================================

SECRET_KEY = (
    os.getenv("SECRET_KEY")
    or os.getenv("DJANGO_SECRET_KEY")
)

if not SECRET_KEY:
    raise RuntimeError(
        (
            "SECRET_KEY is missing. "
            "Add SECRET_KEY to the environment or local .env file."
        )
    )


DEBUG = env_bool(
    "DEBUG",
    env_bool(
        "DJANGO_DEBUG",
        True,
    ),
)


ALLOWED_HOSTS = env_list(
    "ALLOWED_HOSTS",
    "127.0.0.1,localhost",
)

render_hostname = os.getenv(
    "RENDER_EXTERNAL_HOSTNAME"
)

if (
    render_hostname
    and render_hostname not in ALLOWED_HOSTS
):
    ALLOWED_HOSTS.append(
        render_hostname
    )


CSRF_TRUSTED_ORIGINS = env_list(
    "CSRF_TRUSTED_ORIGINS"
)

if render_hostname:
    render_origin = (
        f"https://{render_hostname}"
    )

    if (
        render_origin
        not in CSRF_TRUSTED_ORIGINS
    ):
        CSRF_TRUSTED_ORIGINS.append(
            render_origin
        )


SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)

SESSION_COOKIE_SECURE = not DEBUG

CSRF_COOKIE_SECURE = not DEBUG

SECURE_SSL_REDIRECT = env_bool(
    "SECURE_SSL_REDIRECT",
    not DEBUG,
)


# ==========================================================
# SUPABASE STORAGE ENVIRONMENT
# ==========================================================

SUPABASE_S3_ENDPOINT_URL = os.getenv(
    "SUPABASE_S3_ENDPOINT_URL",
    "",
)

SUPABASE_S3_ACCESS_KEY_ID = os.getenv(
    "SUPABASE_S3_ACCESS_KEY_ID",
    "",
)

SUPABASE_S3_SECRET_ACCESS_KEY = os.getenv(
    "SUPABASE_S3_SECRET_ACCESS_KEY",
    "",
)

SUPABASE_S3_BUCKET = os.getenv(
    "SUPABASE_S3_BUCKET",
    "",
)

SUPABASE_S3_REGION = os.getenv(
    "SUPABASE_S3_REGION",
    "",
)

USE_SUPABASE_STORAGE = all(
    [
        SUPABASE_S3_ENDPOINT_URL,
        SUPABASE_S3_ACCESS_KEY_ID,
        SUPABASE_S3_SECRET_ACCESS_KEY,
        SUPABASE_S3_BUCKET,
        SUPABASE_S3_REGION,
    ]
)


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

    "accounts.apps.AccountsConfig",
    "home",
    "analytics",
    "publications",
    "notifications",
    "workflow",
]

if USE_SUPABASE_STORAGE:
    INSTALLED_APPS.append(
        "storages"
    )


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
    "accounts.middleware.VerifiedEmailRequiredMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if not DEBUG:
    MIDDLEWARE.insert(
        1,
        "whitenoise.middleware.WhiteNoiseMiddleware",
    )


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

DATABASE_URL = os.getenv(
    "DATABASE_URL"
)

if DATABASE_URL:
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }

else:
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

STATIC_URL = "/static/"

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


STORAGES = {
    "default": {
        "BACKEND": (
            "django.core.files.storage."
            "FileSystemStorage"
        ),
    },
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage."
            "StaticFilesStorage"
        ),
    },
}


if not DEBUG:
    STORAGES[
        "staticfiles"
    ] = {
        "BACKEND": (
            "whitenoise.storage."
            "CompressedManifestStaticFilesStorage"
        ),
    }


if USE_SUPABASE_STORAGE:
    AWS_ACCESS_KEY_ID = (
        SUPABASE_S3_ACCESS_KEY_ID
    )

    AWS_SECRET_ACCESS_KEY = (
        SUPABASE_S3_SECRET_ACCESS_KEY
    )

    AWS_STORAGE_BUCKET_NAME = (
        SUPABASE_S3_BUCKET
    )

    AWS_S3_ENDPOINT_URL = (
        SUPABASE_S3_ENDPOINT_URL
    )

    AWS_S3_REGION_NAME = (
        SUPABASE_S3_REGION
    )

    AWS_S3_ADDRESSING_STYLE = "path"

    AWS_S3_SIGNATURE_VERSION = "s3v4"

    AWS_DEFAULT_ACL = None

    AWS_S3_FILE_OVERWRITE = False

    AWS_QUERYSTRING_AUTH = True

    AWS_QUERYSTRING_EXPIRE = 86400

    STORAGES[
        "default"
    ] = {
        "BACKEND": (
            "storages.backends.s3."
            "S3Storage"
        ),
    }


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
# CUSTOM USER / AUTHENTICATION
# ==========================================================

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "accounts.backends."
    "VerifiedEmailModelBackend",
]


# ==========================================================
# EMAIL / ACCOUNT SECURITY
# ==========================================================

SITE_URL = os.getenv(
    "SITE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

# Brevo HTTPS transactional email API.
BREVO_API_KEY = os.getenv(
    "BREVO_API_KEY",
    "",
).strip()

BREVO_API_URL = os.getenv(
    "BREVO_API_URL",
    "https://api.brevo.com/v3/smtp/email",
).strip()

# Local fallback: if no Brevo key is configured, print mail to the terminal.
EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    (
        "accounts.email_backends.BrevoAPIEmailBackend"
        if BREVO_API_KEY
        else "django.core.mail.backends.console.EmailBackend"
    ),
).strip()

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "The Equalizer <noreply@localhost>",
).strip()

BREVO_API_TIMEOUT = int(
    os.getenv(
        "BREVO_API_TIMEOUT",
        "10",
    )
)

# One hour for password-reset links.
PASSWORD_RESET_TIMEOUT = int(
    os.getenv(
        "PASSWORD_RESET_TIMEOUT",
        "3600",
    )
)


# ==========================================================
# AUTH REDIRECTS
# ==========================================================

LOGIN_URL = "/login/"

LOGIN_REDIRECT_URL = (
    "/dashboard/"
)

LOGOUT_REDIRECT_URL = "/"
