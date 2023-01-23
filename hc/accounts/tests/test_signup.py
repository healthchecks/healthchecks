from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.test.utils import override_settings

from hc.accounts.models import Profile, Project
from hc.api.models import Channel, Check


class SignupTestCase(TestCase):
    @override_settings(USE_PAYMENTS=False)
    def test_it_works(self):
        form = {"identity": "alice@example.org", "tz": "Europe/Riga"}

        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "check your email")
        self.assertIn("auto-login", r.cookies)

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
        subject = "Log in to %s" % settings.SITE_NAME
        self.assertEqual(mail.outbox[0].subject, subject)

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

    @override_settings(USE_PAYMENTS=True)
    def test_it_sets_limits(self):
        form = {"identity": "alice@example.org", "tz": ""}

        self.client.post("/accounts/signup/", form)

        profile = Profile.objects.get()
        self.assertEqual(profile.check_limit, 20)
        self.assertEqual(profile.sms_limit, 5)
        self.assertEqual(profile.call_limit, 0)

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_obeys_registration_open(self):
        form = {"identity": "dan@example.org", "tz": ""}

        r = self.client.post("/accounts/signup/", form)
        self.assertEqual(r.status_code, 403)

    def test_it_ignores_case(self):
        form = {"identity": "ALICE@EXAMPLE.ORG", "tz": ""}
        self.client.post("/accounts/signup/", form)

        # There should be exactly one user:
        q = User.objects.filter(email="alice@example.org")
        self.assertTrue(q.exists)

    def test_it_handles_existing_users(self):
        alice = User(username="alice", email="alice@example.org")
        alice.save()

        form = {"identity": "alice@example.org", "tz": ""}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "check your email")
        self.assertIn("auto-login", r.cookies)

        # It should not send an email
        self.assertEqual(len(mail.outbox), 0)

    def test_it_checks_syntax(self):
        form = {"identity": "alice at example org", "tz": ""}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "Enter a valid email address")

    def test_it_checks_length(self):
        aaa = "a" * 300
        form = {"identity": f"alice+{aaa}@example.org", "tz": ""}
        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "Address is too long.")

        self.assertFalse(User.objects.exists())

    @override_settings(USE_PAYMENTS=False)
    def test_it_ignores_bad_tz(self):
        form = {"identity": "alice@example.org", "tz": "Foo/Bar"}

        r = self.client.post("/accounts/signup/", form)
        self.assertContains(r, "check your email")
        self.assertIn("auto-login", r.cookies)

        profile = Profile.objects.get()
        self.assertEqual(profile.tz, "UTC")
