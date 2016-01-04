from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import TestCase

from hc.accounts.models import Profile


class CheckTokenTestCase(TestCase):

    def setUp(self):
        super(CheckTokenTestCase, self).setUp()

        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

        self.profile = Profile(user=self.alice)
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
