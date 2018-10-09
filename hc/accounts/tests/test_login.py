from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings
from hc.accounts.models import Profile
from hc.api.models import Check
from django.conf import settings


class LoginTestCase(TestCase):

    def test_it_sends_link(self):
        form = {"email": "alice@example.org"}

        r = self.client.post("/accounts/login/", form)
        assert r.status_code == 302

        # An user should have been created
        self.assertEqual(User.objects.count(), 1)

        # And email sent
        self.assertEqual(len(mail.outbox), 1)
        subject = "Log in to %s" % settings.SITE_NAME
        self.assertEqual(mail.outbox[0].subject, subject)

        # And check should be associated with the new user
        check = Check.objects.get()
        self.assertEqual(check.name, "My First Check")

    def test_it_pops_bad_link_from_session(self):
        self.client.session["bad_link"] = True
        self.client.get("/accounts/login/")
        assert "bad_link" not in self.client.session

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_obeys_registration_open(self):
        form = {"email": "dan@example.org"}

        r = self.client.post("/accounts/login/", form)
        assert r.status_code == 200
        self.assertContains(r, "Incorrect email")

    def test_it_ignores_ces(self):
        alice = User(username="alice", email="alice@example.org")
        alice.save()

        form = {"email": "ALICE@EXAMPLE.ORG"}

        r = self.client.post("/accounts/login/", form)
        assert r.status_code == 302

        # There should be exactly one user:
        self.assertEqual(User.objects.count(), 1)

        profile = Profile.objects.for_user(alice)
        self.assertIn("login", profile.token)
