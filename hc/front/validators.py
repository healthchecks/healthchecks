from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

from cronsim import CronSim, CronSimError
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from oncalendar import OnCalendar, OnCalendarError

from hc.lib.tz import all_timezones


class WebhookValidator(URLValidator):
    schemes = ["http", "https"]

    def add_tld(self, value: str) -> str:
        fields = list(urlsplit(value))
        hostport = fields[1].rsplit(":", maxsplit=1)
        if "." not in hostport[0].rstrip("."):
            # If netloc has no TLD, URLValidator will reject it.
            # So, add a dummy TLD.
            hostport[0] = hostport[0].rstrip(".") + ".dummytld"
            fields[1] = ":".join(hostport)
            value = urlunsplit(fields)
        return value

    def __call__(self, value: str) -> None:
        super().__call__(self.add_tld(value))


class CronValidator(object):
    message = "Not a valid cron expression."

    def __call__(self, value: str) -> None:
        # Expect 5 components-
        if len(value.split()) != 5:
            raise ValidationError(message=self.message)

        try:
            # Does cronsim accept the schedule?
            it = CronSim(value, datetime(2000, 1, 1))
            # Can it calculate the next datetime?
            next(it)
        except (CronSimError, StopIteration):
            raise ValidationError(message=self.message)


class OnCalendarValidator(object):
    message = "Not a valid OnCalendar expression."

    def __call__(self, value: str) -> None:
        # Expect 1 - 4 components
        for expr in value.strip().split("\n"):
            if len(expr.split()) > 4:
                raise ValidationError(message=self.message)

        try:
            # Does oncalendar accept the schedule?
            it = OnCalendar(value, datetime(2000, 1, 1, tzinfo=timezone.utc))
            # Can it calculate the next datetime?
            next(it)
        except (OnCalendarError, StopIteration):
            raise ValidationError(message=self.message)


class TimezoneValidator(object):
    message = "Not a valid time zone."

    def __call__(self, value: str) -> None:
        if value not in all_timezones:
            raise ValidationError(message=self.message)
