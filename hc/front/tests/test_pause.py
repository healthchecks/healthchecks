from datetime import timedelta as td

from django.utils.timezone import now
from hc.api.models import Check
from hc.test import BaseTestCase


class PauseTestCase(BaseTestCase):

    def setUp(self):
        super(PauseTestCase, self).setUp()
        self.check = Check(user=self.alice, status="up", project=self.project)
        self.check.save()

        self.url = "/checks/%s/pause/" % self.check.code

    def test_it_pauses(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, "/checks/")

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "paused")

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_allows_cross_team_access(self):
        self.bobs_profile.current_team = None
        self.bobs_profile.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, "/checks/")

    def test_it_clears_last_start_alert_after(self):
        self.check.last_start = now()
        self.check.alert_after = self.check.last_start + td(hours=1)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.last_start, None)
        self.assertEqual(self.check.alert_after, None)
