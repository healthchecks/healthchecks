from datetime import timedelta as td

from django.utils.timezone import now
from hc.api.models import Check
from hc.test import BaseTestCase


class PauseTestCase(BaseTestCase):
    def setUp(self):
        super(PauseTestCase, self).setUp()
        self.check = Check.objects.create(project=self.project, status="up")
        self.url = "/checks/%s/pause/" % self.check.code
        self.redirect_url = "/checks/%s/details/" % self.check.code

    def test_it_pauses(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "paused")

    def test_it_rejects_get(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_allows_cross_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

    def test_it_clears_last_start_alert_after(self):
        self.check.last_start = now()
        self.check.alert_after = self.check.last_start + td(hours=1)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.last_start, None)
        self.assertEqual(self.check.alert_after, None)

    def test_it_does_not_redirect_ajax(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.status_code, 200)

    def test_it_requires_rw_access(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)
