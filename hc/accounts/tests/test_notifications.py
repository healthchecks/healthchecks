from hc.test import BaseTestCase


class NotificationsTestCase(BaseTestCase):

    def test_it_saves_reports_allowed_true(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"reports_allowed": "on"}
        r = self.client.post("/accounts/profile/notifications/", form)
        assert r.status_code == 200

        self.alice.profile.refresh_from_db()
        self.assertTrue(self.alice.profile.reports_allowed)

    def test_it_saves_reports_allowed_false(self):
        self.client.login(username="alice@example.org", password="password")

        form = {}
        r = self.client.post("/accounts/profile/notifications/", form)
        assert r.status_code == 200

        self.alice.profile.refresh_from_db()
        self.assertFalse(self.alice.profile.reports_allowed)
