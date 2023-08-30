from __future__ import annotations

from datetime import timedelta as td

from django.utils.timezone import now

from hc.api.models import Check, Flip
from hc.test import BaseTestCase


class PauseTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project, status="up")
        self.url = f"/checks/{self.check.code}/pause/"
        self.redirect_url = f"/checks/{self.check.code}/details/"

    def test_it_pauses(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "paused")

        # It should also create a Flip object, needed for accurate downtime
        # tracking in Check.downtimes():
        flip = Flip.objects.get()
        self.assertEqual(flip.old_status, "up")
        self.assertEqual(flip.new_status, "paused")
        # should be marked as processed from the beginning, so sendalerts ignores it
        self.assertTrue(flip.processed)

    def test_it_rejects_get(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 405)

    def test_it_allows_cross_team_access(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertRedirects(r, self.redirect_url)

    def test_it_clears_last_start_alert_after(self) -> None:
        self.check.last_start = now()
        self.check.alert_after = self.check.last_start + td(hours=1)
        self.check.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url)

        self.check.refresh_from_db()
        self.assertEqual(self.check.last_start, None)
        self.assertEqual(self.check.alert_after, None)

    def test_it_does_not_redirect_ajax(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.status_code, 200)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url)
        self.assertEqual(r.status_code, 403)

    def test_it_clears_next_nag_date(self) -> None:
        self.profile.nag_period = td(hours=1)
        self.profile.next_nag_date = now() + td(minutes=30)
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url)

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.next_nag_date)
