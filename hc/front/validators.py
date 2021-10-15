from datetime import datetime

from cronsim import CronSim
from django.core.exceptions import ValidationError
from urllib.parse import urlparse
from pytz import all_timezones


class WebhookValidator(object):
    message = "Enter a valid URL."

    def __call__(self, value):
        parsed = urlparse(value)
        if parsed.scheme not in ("http", "https"):
            raise ValidationError(message=self.message)

        if parsed.hostname in ("127.0.0.1", "localhost"):
            raise ValidationError(message=self.message)


class CronExpressionValidator(object):
    message = "Not a valid cron expression."

    def __call__(self, value):
        # Expect 5 components-
        if len(value.split()) != 5:
            raise ValidationError(message=self.message)

        try:
            # Does cronsim accept the schedule?
            it = CronSim(value, datetime(2000, 1, 1))
            # Can it calculate the next datetime?
            next(it)
        except:
            raise ValidationError(message=self.message)


class TimezoneValidator(object):
    message = "Not a valid time zone."

    def __call__(self, value):
        if value not in all_timezones:
            raise ValidationError(message=self.message)
