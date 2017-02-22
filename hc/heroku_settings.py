import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SITE_ROOT = os.getenv('SITE_ROOT', "https://my-monitoring-project.com")
SITE_NAME = os.getenv('SITE_NAME', "My Monitoring Project")
DEFAULT_FROM_EMAIL = os.getenv('FROM_EMAIL', "noreply@my-monitoring-project.com")

import herokuify
from herokuify.common import *
from herokuify.mail.mailgun import *

DATABASES = herokuify.get_db_config()

DEBUG = False
SECRET_KEY = os.getenv('SECRET_KEY', "---")

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/

STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'

import sys
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt' : "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'stream': sys.stdout,
        },
    },
    'loggers': {
        'django': {
            'handlers':['console'],
            'propagate': True,
            'level':'DEBUG',
        },
        'MYAPP': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    }
}
