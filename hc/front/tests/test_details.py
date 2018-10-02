from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class DetailsTestCase(BaseTestCase):

    def setUp(self):
        super(DetailsTestCase, self).setUp()
        self.check = Check(user=self.alice)
        self.check.save()

        ping = Ping(owner=self.check)
        ping.save()

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
        assert r.status_code == 403

    def test_it_shows_cron_expression(self):
        self.check.kind = "cron"
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Cron Expression", status_code=200)
