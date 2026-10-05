from __future__ import annotations

from datetime import timedelta as td

from django.core import mail
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.logs.management.commands.sendlogs import Command
from hc.logs.models import Record
from hc.test import BaseTestCase


@override_settings(ADMINS=["admin@example.org"])
class SendLogsTestCase(BaseTestCase):
    def test_it_sends_email(self) -> None:
        Record.objects.create(
            host="testhost",
            name="hc.test",
            level=20,
            message="test message",
            traceback="",
        )

        result = Command().handle()
        self.assertEqual(result, "Done, 1 new log record.")

        email = mail.outbox[0]
        self.assertEqual(
            email.subject, "[Django] 1 new log record in the last 24 hours"
        )

    def test_it_removes_records_older_than_week(self) -> None:
        Record.objects.create(
            created=now() - td(days=8),
            host="testhost",
            name="hc.test",
            level=20,
            message="test message",
            traceback="",
        )

        result = Command().handle()
        self.assertEqual(result, "Done, no new log records.")

        self.assertEqual(Record.objects.count(), 0)
