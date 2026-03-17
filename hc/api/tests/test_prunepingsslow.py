from __future__ import annotations

from unittest.mock import Mock, patch

from hc.api.management.commands.prunepingsslow import Command
from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class PrunePingsSlowTestCase(BaseTestCase):
    @patch("hc.api.models.remove_objects", autospec=True)
    def test_it_works(self, remove_objects: Mock) -> None:
        check = Check.objects.create(project=self.project, n_pings=101)
        Ping.objects.create(owner=check, n=1)
        Command(stdout=Mock()).handle()

        # The ping should have been deleted
        self.assertFalse(Ping.objects.exists())
