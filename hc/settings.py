"""
Django settings for healthchecks project.

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.0/ref/settings/
"""

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def envbool(s, default):
    v = os.getenv(s, default=default)
    if v not in ("", "True", "False"):
        msg = "Unexpected value %s=%s, use 'True' or 'False'" % (s, v)
        raise Exception(msg)
    return v == "True"


def envint(s, default):
    v = os.getenv(s, default)
    if v == "None":
        return None

    return int(v)


SECRET_KEY = os.getenv("SECRET_KEY", "---")
METRICS_KEY = os.getenv("METRICS_KEY")
DEBUG = envbool("DEBUG", "True")
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "healthchecks@example.org")
SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL")
USE_PAYMENTS = envbool("USE_PAYMENTS", "False")
REGISTRATION_OPEN = envbool("REGISTRATION_OPEN", "True")
VERSION = ""
with open(os.path.join(BASE_DIR, "CHANGELOG.md"), encoding="utf-8") as f:
    for line in f.readlines():
        if line.startswith("## v"):
            VERSION = line.split()[1]
            break


INSTALLED_APPS = (
    "hc.accounts",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.humanize",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "compressor",
    "hc.api",
    "hc.front",
    "hc.payments",
)


MIDDLEWARE = (
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "hc.accounts.middleware.CustomHeaderMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "hc.accounts.middleware.TeamAccessMiddleware",
)

AUTHENTICATION_BACKENDS = (
    "hc.accounts.backends.EmailBackend",
    "hc.accounts.backends.ProfileBackend",
)

REMOTE_USER_HEADER = os.getenv("REMOTE_USER_HEADER")
if REMOTE_USER_HEADER:
    AUTHENTICATION_BACKENDS = ("hc.accounts.backends.CustomHeaderBackend",)

ROOT_URLCONF = "hc.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "hc.front.context_processors.branding",
                "hc.payments.context_processors.payments",
            ]
        },
    }
]

WSGI_APPLICATION = "hc.wsgi.application"
TEST_RUNNER = "hc.api.tests.CustomRunner"


# Default database engine is SQLite. So one can just check out code,
# install requirements.txt and do manage.py runserver and it works
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("DB_NAME", BASE_DIR + "/hc.sqlite"),
    }
}

# You can switch database engine to postgres or mysql using environment
# variable 'DB'. Travis CI does this.
if os.getenv("DB") == "postgres":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.getenv("DB_HOST", ""),
            "PORT": os.getenv("DB_PORT", ""),
            "NAME": os.getenv("DB_NAME", "hc"),
            "USER": os.getenv("DB_USER", "postgres"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "CONN_MAX_AGE": envint("DB_CONN_MAX_AGE", "0"),
            "TEST": {"CHARSET": "UTF8"},
            "OPTIONS": {
                "sslmode": os.getenv("DB_SSLMODE", "prefer"),
                "target_session_attrs": os.getenv(
                    "DB_TARGET_SESSION_ATTRS", "read-write"
                ),
            },
        }
    }

if os.getenv("DB") == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "HOST": os.getenv("DB_HOST", ""),
            "PORT": os.getenv("DB_PORT", ""),
            "NAME": os.getenv("DB_NAME", "hc"),
            "USER": os.getenv("DB_USER", "root"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "TEST": {"CHARSET": "UTF8"},
        }
    }

USE_TZ = True
TIME_ZONE = "UTC"
LOCALE_PATHS = (os.path.join(BASE_DIR, "locale"),)

SITE_ROOT = os.getenv("SITE_ROOT", "http://localhost:8000")
SITE_NAME = os.getenv("SITE_NAME", "Mychecks")
SITE_LOGO_URL = os.getenv("SITE_LOGO_URL")
MASTER_BADGE_LABEL = os.getenv("MASTER_BADGE_LABEL", SITE_NAME)
PING_ENDPOINT = os.getenv("PING_ENDPOINT", SITE_ROOT + "/ping/")
PING_EMAIL_DOMAIN = os.getenv("PING_EMAIL_DOMAIN", "localhost")
PING_BODY_LIMIT = envint("PING_BODY_LIMIT", "10000")
STATIC_URL = "/static/"
STATICFILES_DIRS = [os.path.join(BASE_DIR, "static")]
STATIC_ROOT = os.path.join(BASE_DIR, "static-collected")
STATICFILES_FINDERS = (
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
    "compressor.finders.CompressorFinder",
)
COMPRESS_OFFLINE = True
COMPRESS_CSS_HASHING_METHOD = "content"


def immutable_file_test(path, url):
    return url.startswith("/static/CACHE/") or url.startswith("/static/fonts/")


WHITENOISE_IMMUTABLE_FILE_TEST = immutable_file_test

# SMTP credentials for sending email
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = envint("EMAIL_PORT", "587")
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = envbool("EMAIL_USE_TLS", "True")
EMAIL_USE_SSL = envbool("EMAIL_USE_SSL", "False")
EMAIL_USE_VERIFICATION = envbool("EMAIL_USE_VERIFICATION", "True")

# WebAuthn
RP_ID = os.getenv("RP_ID")

# Object storage credentials for storing large ping bodies.
# (Optional. If not specified, will store ping bodies in the database.)
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY")
S3_ENDPOINT = os.getenv("S3_ENDPOINT")
S3_REGION = os.getenv("S3_REGION")
S3_BUCKET = os.getenv("S3_BUCKET")
S3_TIMEOUT = envint("S3_TIMEOUT", 60)

# Integrations

# Apprise
APPRISE_ENABLED = envbool("APPRISE_ENABLED", "False")

# Discord integration
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")


# LINE Notify
LINENOTIFY_CLIENT_ID = os.getenv("LINENOTIFY_CLIENT_ID")
LINENOTIFY_CLIENT_SECRET = os.getenv("LINENOTIFY_CLIENT_SECRET")

# Matrix
MATRIX_HOMESERVER = os.getenv("MATRIX_HOMESERVER")
MATRIX_USER_ID = os.getenv("MATRIX_USER_ID")
MATRIX_ACCESS_TOKEN = os.getenv("MATRIX_ACCESS_TOKEN")

# Mattermost
MATTERMOST_ENABLED = envbool("MATTERMOST_ENABLED", "True")

# MS Teams
MSTEAMS_ENABLED = envbool("MSTEAMS_ENABLED", "True")

# Opsgenie
OPSGENIE_ENABLED = envbool("OPSGENIE_ENABLED", "True")

# PagerTree
PAGERTREE_ENABLED = envbool("PAGERTREE_ENABLED", "True")

# PagerDuty
PD_ENABLED = envbool("PD_ENABLED", "True")
PD_APP_ID = os.getenv("PD_APP_ID")

# Prometheus
PROMETHEUS_ENABLED = envbool("PROMETHEUS_ENABLED", "True")

# Pushover integration
PUSHOVER_API_TOKEN = os.getenv("PUSHOVER_API_TOKEN")
PUSHOVER_SUBSCRIPTION_URL = os.getenv("PUSHOVER_SUBSCRIPTION_URL")
PUSHOVER_EMERGENCY_RETRY_DELAY = int(os.getenv("PUSHOVER_EMERGENCY_RETRY_DELAY", "300"))
PUSHOVER_EMERGENCY_EXPIRATION = int(os.getenv("PUSHOVER_EMERGENCY_EXPIRATION", "86400"))

# Pushbullet integration
PUSHBULLET_CLIENT_ID = os.getenv("PUSHBULLET_CLIENT_ID")
PUSHBULLET_CLIENT_SECRET = os.getenv("PUSHBULLET_CLIENT_SECRET")

# Local shell commands
SHELL_ENABLED = envbool("SHELL_ENABLED", "False")

# Signal
SIGNAL_CLI_SOCKET = os.getenv("SIGNAL_CLI_SOCKET")

# Slack integration
SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_ENABLED = envbool("SLACK_ENABLED", "True")

# Spike.sh
SPIKE_ENABLED = envbool("SPIKE_ENABLED", "True")

# Telegram integration -- override in local_settings.py
TELEGRAM_BOT_NAME = os.getenv("TELEGRAM_BOT_NAME", "ExampleBot")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# SMS and WhatsApp (Twilio) integration
TWILIO_ACCOUNT = os.getenv("TWILIO_ACCOUNT")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_FROM = os.getenv("TWILIO_FROM")
TWILIO_USE_WHATSAPP = envbool("TWILIO_USE_WHATSAPP", "False")

# Trello
TRELLO_APP_KEY = os.getenv("TRELLO_APP_KEY")

# VictorOps
VICTOROPS_ENABLED = envbool("VICTOROPS_ENABLED", "True")

# Webhooks
WEBHOOKS_ENABLED = envbool("WEBHOOKS_ENABLED", "True")

# Zulip
ZULIP_ENABLED = envbool("ZULIP_ENABLED", "True")

# Read additional configuration from hc/local_settings.py if it exists
if os.path.exists(os.path.join(BASE_DIR, "hc/local_settings.py")):
    from .local_settings import *
