from __future__ import annotations

from datetime import timedelta as td
from typing import Any

from django.conf import settings
from django.core.mail import mail_admins
from django.core.management.base import BaseCommand
from django.urls import reverse
from django.utils.timezone import now

from hc.logs.models import Record

YEAR_AGO = now() - td(days=365)


class Command(BaseCommand):
    help = """Send notification to admins about new log events."""

    def handle(self, **options: Any) -> str:
        threshold = now() - td(hours=24)
        count = Record.objects.filter(created__gt=threshold).count()
        if count > 0:
            url = settings.SITE_ROOT + reverse("admin:logs_record_changelist")
            s_maybe = "" if count == 1 else "s"
            message = f"{count} new log record{s_maybe} in the last 24 hours"
            html_message = f"""
            {count} new log record{s_maybe} in the last 24 hours.<br />
            <a href="{url}">Show log records</a>.
            """
            mail_admins(message, message, html_message=html_message)
            return f"Done, {count} new log record{s_maybe}."

        return "Done, no new log records."
