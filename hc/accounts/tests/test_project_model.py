from __future__ import annotations

from hc.accounts.models import Member, Project
from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class ProjectModelTestCase(BaseTestCase):
    def test_num_checks_available_handles_multiple_projects(self) -> None:
        # One check in Alice's primary project:
        Check.objects.create(project=self.project)

        # One check in Alice's secondary project:
        p2 = Project.objects.create(owner=self.alice)
        Check.objects.create(project=p2)

        self.assertEqual(self.project.num_checks_available(), 18)

    def test_it_handles_zero_broken_channels(self) -> None:
        Channel.objects.create(kind="webhook", last_error="", project=self.project)

        self.assertFalse(self.project.have_channel_issues())

    def test_it_handles_one_broken_channel(self) -> None:
        Channel.objects.create(kind="webhook", last_error="x", project=self.project)

        self.assertTrue(self.project.have_channel_issues())

    def test_it_handles_no_channels(self) -> None:
        # It's an issue if the project has no channels at all:
        self.assertTrue(self.project.have_channel_issues())
