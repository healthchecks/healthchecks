from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test import TestCase


class CheckTokenTestCase(TestCase):

    def setUp(self):
        super(CheckTokenTestCase, self).setUp()

        self.alice = User(username="alice")
        self.alice.set_password("secret-token")
        self.alice.save()

    def test_it_redirects(self):
        r = self.client.get("/accounts/check_token/alice/secret-token/")
        assert r.status_code == 302

        # After login, password should be unusable
        self.alice.refresh_from_db()
        assert not self.alice.has_usable_password()

    def test_it_redirects_already_logged_in(self):
        # Login
        self.client.get("/accounts/check_token/alice/secret-token/")

        # Login again, when already authenticated
        r = self.client.get("/accounts/check_token/alice/secret-token/")
        assert r.status_code == 302

    def test_it_redirects_bad_login(self):
        # Login with a bad token
        r = self.client.get("/accounts/check_token/alice/invalid-token/")
        assert r.status_code == 302
        assert r.url.endswith(reverse("hc-login"))
        assert self.client.session["bad_link"]
