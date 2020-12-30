from datetime import timedelta as td

from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class DetailsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)

        ping = Ping.objects.create(owner=self.check)

        # Older MySQL versions don't store microseconds. This makes sure
        # the ping is older than any notifications we may create later:
        ping.created = "2000-01-01T00:00:00+00:00"
        ping.save()

        self.url = "/checks/%s/details/" % self.check.code

    def test_it_works(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "How To Ping", status_code=200)
        # The page should contain timezone strings
        self.assertContains(r, "Europe/Riga")

    def test_it_checks_ownership(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_shows_cron_expression(self):
        self.check.kind = "cron"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Cron Expression", status_code=200)

    def test_it_allows_cross_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_shows_new_check_notice(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?new")
        self.assertContains(r, "Your new check is ready!", status_code=200)

    def test_it_hides_actions_from_readonly_users(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, "edit-name", status_code=200)
        self.assertNotContains(r, "edit-desc")
        self.assertNotContains(r, "Filtering Rules")
        self.assertNotContains(r, "pause-btn")
        self.assertNotContains(r, "Change Schedule")
        self.assertNotContains(r, "Create a Copy&hellip;")
        self.assertNotContains(r, "transfer-btn")
        self.assertNotContains(r, "details-remove-check")

    def test_it_hides_resume_action_from_readonly_users(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.check.status = "paused"
        self.check.manual_resume = True
        self.check.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)

        self.assertNotContains(r, "resume-btn", status_code=200)

    def test_crontab_example_guesses_schedules(self):
        self.client.login(username="alice@example.org", password="password")

        pairs = [
            (td(minutes=1), "* * * * *"),
            (td(minutes=12), "*/12 * * * *"),
            (td(hours=1), "0 * * * *"),
            (td(hours=6), "0 */6 * * *"),
            (td(days=1), "0 0 * * *"),
        ]

        for timeout, expression in pairs:
            self.check.timeout = timeout
            self.check.save()

            r = self.client.get(self.url)
            self.assertContains(r, f"{expression} /your/command.sh")
            self.assertNotContains(r, 'FIXME: replace "* * * * *"')

    def test_crontab_example_handles_unsupported_timeout_values(self):
        self.client.login(username="alice@example.org", password="password")

        self.check.timeout = td(minutes=13)
        self.check.save()

        r = self.client.get(self.url)
        self.assertContains(r, f"* * * * * /your/command.sh")
        self.assertContains(r, 'FIXME: replace "* * * * *"')
