from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(SHELL_ENABLED=True)
class AddShellTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.url = f"/projects/{self.project.code}/add_shell/"

    @override_settings(SHELL_ENABLED=False)
    def test_it_is_disabled_by_default(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Executes a local shell command")

    def test_it_adds_two_commands_and_redirects(self) -> None:
        form = {"cmd_down": "logger down", "cmd_up": "logger up"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.project, self.project)
        self.assertEqual(c.shell.cmd_down, "logger down")
        self.assertEqual(c.shell.cmd_up, "logger up")

    def test_it_adds_webhook_using_team_access(self) -> None:
        form = {"cmd_down": "logger down", "cmd_up": "logger up"}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.project, self.project)
        self.assertEqual(c.shell.cmd_down, "logger down")

    def test_it_handles_empty_down_command(self) -> None:
        form = {"cmd_down": "", "cmd_up": "logger up"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.shell.cmd_down, "")
        self.assertEqual(c.shell.cmd_up, "logger up")

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
