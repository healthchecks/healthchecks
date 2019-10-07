from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class DetailsTestCase(BaseTestCase):
    def setUp(self):
        super(DetailsTestCase, self).setUp()
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
        self.bobs_profile.current_project = None
        self.bobs_profile.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

    def test_it_shows_new_check_notice(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url + "?new")
        self.assertContains(r, "Your new check is ready!", status_code=200)
