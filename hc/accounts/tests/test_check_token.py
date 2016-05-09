from django.contrib.auth.hashers import make_password
from hc.test import BaseTestCase


class CheckTokenTestCase(BaseTestCase):

    def setUp(self):
        super(CheckTokenTestCase, self).setUp()
        self.profile.token = make_password("secret-token")
        self.profile.save()

    def test_it_redirects(self):
        r = self.client.get("/accounts/check_token/alice/secret-token/")
        self.assertRedirects(r, "/checks/")

        # After login, token should be blank
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.token, "")

    def test_it_redirects_already_logged_in(self):
        # Login
        self.client.login(username="alice@example.org", password="password")

        # Login again, when already authenticated
        r = self.client.get("/accounts/check_token/alice/secret-token/")
        self.assertRedirects(r, "/checks/")

    def test_it_redirects_bad_login(self):
        # Login with a bad token
        url = "/accounts/check_token/alice/invalid-token/"
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, "/accounts/login/")
        self.assertContains(r, "incorrect or expired")
