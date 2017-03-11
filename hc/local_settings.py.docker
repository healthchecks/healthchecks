"""
Local settings for the HealthChecks app
"""

import os

ALLOWED_HOSTS = ['*']
DEBUG = os.getenv('HEALTHCHECKS_DEBUG', False)

HOST = os.getenv('HEALTHCHECKS_HOST', "localhost")
SITE_ROOT = os.getenv('HEALTHCHECKS_SITE_ROOT', "http://localhost:9090")
PING_ENDPOINT = SITE_ROOT + "/ping/"

DEFAULT_FROM_EMAIL = os.getenv('HEALTHCHECKS_EMAIL_FROM', "healthchecks@example.org")
EMAIL_HOST = os.getenv('HEALTHCHECKS_EMAIL_HOST', "localhost")
EMAIL_PORT = os.getenv('HEALTHCHECKS_EMAIL_PORT', 25)
EMAIL_HOST_USER = os.getenv('HEALTHCHECKS_EMAIL_USER', "")
EMAIL_HOST_PASSWORD = os.getenv('HEALTHCHECKS_EMAIL_PASSWORD', "")

if os.environ.get("HEALTHCHECKS_DB") == "postgres":
    DATABASES = {
        'default': {
            'ENGINE':   'django.db.backends.postgresql',
            'NAME':     os.getenv("HEALTHCHECKS_DB_NAME", "hc"),
            'USER':     os.getenv('HEALTHCHECKS_DB_USER', "postgres"),
            'PASSWORD': os.getenv('HEALTHCHECKS_DB_PASSWORD', ""),
            'HOST':     os.getenv('HEALTHCHECKS_DB_HOST', "localhost"),
            'TEST': {'CHARSET': 'UTF8'}
        }
    }

if os.environ.get("HEALTHCHECKS_DB") == "mysql":
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'USER':     os.getenv('HEALTHCHECKS_DB_USER', "root"),
            'PASSWORD': os.getenv('HEALTHCHECKS_DB_PASSWORD', ""),
            'NAME':     os.getenv("HEALTHCHECKS_DB_NAME", "hc"),
            'HOST': os.getenv('HEALTHCHECKS_DB_HOST', "localhost"),
            'TEST': {'CHARSET': 'UTF8'}
        }
    }
