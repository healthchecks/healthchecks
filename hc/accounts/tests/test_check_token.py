from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.test import TestCase

from hc.accounts.models import Profile


class CheckTokenTestCase(TestCase):

    def setUp(self):
        super(CheckTokenTestCase, self).setUp()

        self.alice = User(username="alice")
        self.alice.save()

        self.profile = Profile(user=self.alice)
        self.profile.token = make_password("secret-token")
        self.profile.save()

    def test_it_redirects(self):
        r = self.client.get("/accounts/check_token/alice/secret-token/")
        self.assertRedirects(r, "/checks/")

        # After login, password should be unusable
        self.alice.refresh_from_db()
        assert not self.alice.has_usable_password()

    def test_it_redirects_already_logged_in(self):
        # Login
        self.client.get("/accounts/check_token/alice/secret-token/")

        # Login again, when already authenticated
        r = self.client.get("/accounts/check_token/alice/secret-token/")
        self.assertRedirects(r, "/checks/")

    def test_it_redirects_bad_login(self):
        # Login with a bad token
        url = "/accounts/check_token/alice/invalid-token/"
        r = self.client.get(url, follow=True)
        self.assertRedirects(r, "/accounts/login/")
        self.assertContains(r, "incorrect or expired")
