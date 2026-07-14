from __future__ import annotations

from unittest.mock import Mock, patch

from django.core import mail
from django.utils.timezone import now

from hc.accounts.management.commands.sendflappingnotices import Command
from hc.api.models import Check, Flip
from hc.test import BaseTestCase

MOCK_SLEEP = Mock()


@patch("hc.accounts.management.commands.sendflappingnotices.time.sleep", MOCK_SLEEP)
@patch("hc.accounts.management.commands.sendflappingnotices.FLIP_THRESHOLD", 3)
class SendFlappingNoticesTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        c = Check.objects.create(project=self.project, name="Foo")
        nao = now()
        for i in range(0, 4):
            Flip.objects.create(owner=c, created=nao, old_status="new", new_status="up")

    def test_it_sends_notice(self) -> None:
        cmd = Command(stdout=Mock())
        cmd.handle()

        tos = set()
        for email in mail.outbox:
            self.assertEqual(email.subject, """The Check "Foo" Is Flapping""")
            tos.update(email.to)

        self.assertIn("alice@example.org", tos)
        # Team members should receive this too
        self.assertIn("bob@example.org", tos)
