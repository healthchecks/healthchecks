from hc.test import BaseTestCase


class SetPasswordTestCase(BaseTestCase):
    def test_it_shows_form(self):
        token = self.profile.prepare_token("set-password")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/set_password/%s/" % token)
        self.assertEqual(r.status_code, 200)

        self.assertContains(r, "Please pick a password")

    def test_it_checks_token(self):
        self.profile.prepare_token("set-password")
        self.client.login(username="alice@example.org", password="password")

        # GET
        r = self.client.get("/accounts/set_password/invalid-token/")
        self.assertEqual(r.status_code, 400)

        # POST
        r = self.client.post("/accounts/set_password/invalid-token/")
        self.assertEqual(r.status_code, 400)

    def test_it_sets_password(self):
        token = self.profile.prepare_token("set-password")

        self.client.login(username="alice@example.org", password="password")
        payload = {"password": "correct horse battery staple"}
        r = self.client.post("/accounts/set_password/%s/" % token, payload)
        self.assertEqual(r.status_code, 302)

        old_password = self.alice.password
        self.alice.refresh_from_db()
        self.assertNotEqual(self.alice.password, old_password)

    def test_post_checks_length(self):
        token = self.profile.prepare_token("set-password")

        self.client.login(username="alice@example.org", password="password")
        payload = {"password": "abc"}
        r = self.client.post("/accounts/set_password/%s/" % token, payload)
        self.assertEqual(r.status_code, 200)

        old_password = self.alice.password
        self.alice.refresh_from_db()
        self.assertEqual(self.alice.password, old_password)
