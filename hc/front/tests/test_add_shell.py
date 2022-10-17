from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel
from hc.test import BaseTestCase


@override_settings(SHELL_ENABLED=True)
class AddShellTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.url = "/projects/%s/add_shell/" % self.project.code

    @override_settings(SHELL_ENABLED=False)
    def test_it_is_disabled_by_default(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Executes a local shell command")

    def test_it_adds_two_commands_and_redirects(self):
        form = {"cmd_down": "logger down", "cmd_up": "logger up"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.project, self.project)
        self.assertEqual(c.cmd_down, "logger down")
        self.assertEqual(c.cmd_up, "logger up")

    def test_it_adds_webhook_using_team_access(self):
        form = {"cmd_down": "logger down", "cmd_up": "logger up"}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.project, self.project)
        self.assertEqual(c.cmd_down, "logger down")

    def test_it_handles_empty_down_command(self):
        form = {"cmd_down": "", "cmd_up": "logger up"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.cmd_down, "")
        self.assertEqual(c.cmd_up, "logger up")

    def test_it_requires_rw_access(self):
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)
