from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings

from hc.accounts.models import Profile, Project
from hc.api.models import Channel, Check, TokenBucket


@override_settings(REGISTRATION_OPEN=True)
class SignupTestCase(TestCase):
    @override_settings(USE_PAYMENTS=False, SESSION_COOKIE_SECURE=False)
    def test_it_works(self) -> None:
        form = {"identity": "alice@example.org", "tz": "Europe/Riga"}

        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "check your email")

        self.assertEqual(r.cookies["auto-login"].value, "1")
        self.assertEqual(r.cookies["auto-login"]["samesite"], "Lax")
        self.assertTrue(r.cookies["auto-login"]["httponly"])
        self.assertFalse(r.cookies["auto-login"]["secure"])

        # An user should have been created
        user = User.objects.get()

        # A profile should have been created
        profile = Profile.objects.get()
        self.assertEqual(profile.check_limit, 10000)
        self.assertEqual(profile.sms_limit, 10000)
        self.assertEqual(profile.call_limit, 10000)
        self.assertEqual(profile.tz, "Europe/Riga")

        # And email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, f"Log in to {settings.SITE_NAME}")

        # A project should have been created
        project = Project.objects.get()
        self.assertEqual(project.owner, user)
        self.assertEqual(project.badge_key, user.username)

        # And check should be associated with the new user
        check = Check.objects.get()
        self.assertEqual(check.name, "My First Check")
        self.assertEqual(check.slug, "my-first-check")
        self.assertEqual(check.project, project)

        # A channel should have been created
        channel = Channel.objects.get()
        self.assertEqual(channel.project, project)

    @override_settings(SESSION_COOKIE_SECURE=True)
    def test_it_sets_secure_autologin_cookie(self) -> None:
        form = {"identity": "alice@example.org", "tz": "Europe/Riga"}
        r = self.client.post("/accounts/signup/", form)
        self.assertTrue(r.cookies["auto-login"]["secure"])

    def test_it_requires_unauthenticated_user(self) -> None:
        self.alice = User(username="alice", email="alice@example.org")
        self.alice.set_password("password")
        self.alice.save()

        self.client.login(username="alice@example.org", password="password")
        form = {"identity": "alice@example.org", "tz": "Europe/Riga"}
        r = self.client.post("/accounts/signup/", form)
        self.assertEqual(r.status_code, 403)

    @override_settings(USE_PAYMENTS=True)
    def test_it_sets_limits(self) -> None:
        form = {"identity": "alice@example.org", "tz": ""}

        self.client.post("/accounts/signup/", form)

        profile = Profile.objects.get()
        self.assertEqual(profile.check_limit, 20)
        self.assertEqual(profile.sms_limit, 5)
        self.assertEqual(profile.call_limit, 0)

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_obeys_registration_open(self) -> None:
        form = {"identity": "dan@example.org", "tz": ""}

        r = self.client.post("/accounts/signup/", form)
        self.assertEqual(r.status_code, 403)

    def test_it_ignores_case(self) -> None:
        form = {"identity": "ALICE@EXAMPLE.ORG", "tz": ""}
        self.client.post("/accounts/signup/", form)

        # There should be exactly one user:
        q = User.objects.filter(email="alice@example.org")
        self.assertTrue(q.exists)

    def test_it_handles_existing_users(self) -> None:
        alice = User(username="alice", email="alice@example.org")
        alice.save()

        form = {"identity": "alice@example.org", "tz": ""}
        r = self.client.post("/accounts/signup/", form)
        # It should send the same response and cookies as in normal signup
        self.assertContains(r, "check your email")
        self.assertEqual(r.cookies["auto-login"].value, "1")

        # There should still be a single user
        self.assertEqual(User.objects.count(), 1)

        # It should send a normal sign-in email
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, f"Log in to {settings.SITE_NAME}")

    def test_it_checks_syntax(self) -> None:
        form = {"identity": "alice at example org", "tz": ""}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "Enter a valid email address")

    def test_it_checks_length(self) -> None:
        aaa = "a" * 300
        form = {"identity": f"alice+{aaa}@example.org", "tz": ""}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "Address is too long.")

        self.assertFalse(User.objects.exists())

    @override_settings(USE_PAYMENTS=False)
    def test_it_ignores_bad_tz(self) -> None:
        form = {"identity": "alice@example.org", "tz": "Foo/Bar"}

        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "check your email")

        profile = Profile.objects.get()
        self.assertEqual(profile.tz, "UTC")

    def test_it_rate_limits_client_ips(self) -> None:
        obj = TokenBucket(value="auth-ip-127.0.0.1")
        obj.tokens = 0
        obj.save()

        form = {"identity": "alice@example.org", "tz": ""}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "please try later")

    def test_rate_limiter_uses_x_forwarded_for(self) -> None:
        obj = TokenBucket(value="auth-ip-127.0.0.2")
        obj.tokens = 0
        obj.save()

        form = {"identity": "alice@example.org", "tz": ""}
        xff = "127.0.0.2:1234,127.0.0.3"
        r = self.client.post("/accounts/signup/", form, HTTP_X_FORWARDED_FOR=xff)
        self.assertContains(r, "please try later")
