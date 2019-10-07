from django.conf import settings
from django.core import mail
from django.test.utils import override_settings
from hc.api.models import Check, TokenBucket
from hc.test import BaseTestCase


class LoginTestCase(BaseTestCase):
    def setUp(self):
        super(LoginTestCase, self).setUp()
        self.checks_url = "/projects/%s/checks/" % self.project.code

    def test_it_sends_link(self):
        form = {"identity": "alice@example.org"}

        r = self.client.post("/accounts/login/", form)
        self.assertRedirects(r, "/accounts/login_link_sent/")

        # And email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        subject = "Log in to %s" % settings.SITE_NAME
        self.assertEqual(mail.outbox[0].subject, subject)

    def test_it_sends_link_with_next(self):
        form = {"identity": "alice@example.org"}

        r = self.client.post("/accounts/login/?next=/integrations/add_slack/", form)
        self.assertRedirects(r, "/accounts/login_link_sent/")

        # The check_token link should have a ?next= query parameter:
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        self.assertTrue("/?next=/integrations/add_slack/" in body)

    @override_settings(SECRET_KEY="test-secret")
    def test_it_rate_limits_emails(self):
        # "d60d..." is sha1("alice@example.orgtest-secret")
        obj = TokenBucket(value="em-d60db3b2343e713a4de3e92d4eb417e4f05f06ab")
        obj.tokens = 0
        obj.save()

        form = {"identity": "alice@example.org"}

        r = self.client.post("/accounts/login/", form)
        self.assertContains(r, "Too many attempts")

        # No email should have been sent
        self.assertEqual(len(mail.outbox), 0)

    def test_it_pops_bad_link_from_session(self):
        self.client.session["bad_link"] = True
        self.client.get("/accounts/login/")
        assert "bad_link" not in self.client.session

    def test_it_ignores_case(self):
        form = {"identity": "ALICE@EXAMPLE.ORG"}

        r = self.client.post("/accounts/login/", form)
        self.assertRedirects(r, "/accounts/login_link_sent/")

        self.profile.refresh_from_db()
        self.assertIn("login", self.profile.token)

    def test_it_handles_password(self):
        form = {"action": "login", "email": "alice@example.org", "password": "password"}

        r = self.client.post("/accounts/login/", form)
        self.assertRedirects(r, self.checks_url)

    @override_settings(SECRET_KEY="test-secret")
    def test_it_rate_limits_password_attempts(self):
        # "d60d..." is sha1("alice@example.orgtest-secret")
        obj = TokenBucket(value="pw-d60db3b2343e713a4de3e92d4eb417e4f05f06ab")
        obj.tokens = 0
        obj.save()

        form = {"action": "login", "email": "alice@example.org", "password": "password"}

        r = self.client.post("/accounts/login/", form)
        self.assertContains(r, "Too many attempts")

    def test_it_handles_password_login_with_redirect(self):
        check = Check.objects.create(project=self.project)

        form = {"action": "login", "email": "alice@example.org", "password": "password"}

        samples = ["/integrations/add_slack/", "/checks/%s/details/" % check.code]

        for s in samples:
            r = self.client.post("/accounts/login/?next=%s" % s, form)
            self.assertRedirects(r, s)

    def test_it_handles_bad_next_parameter(self):
        form = {"action": "login", "email": "alice@example.org", "password": "password"}

        r = self.client.post("/accounts/login/?next=/evil/", form)
        self.assertRedirects(r, self.checks_url)

    def test_it_handles_wrong_password(self):
        form = {
            "action": "login",
            "email": "alice@example.org",
            "password": "wrong password",
        }

        r = self.client.post("/accounts/login/", form)
        self.assertContains(r, "Incorrect email or password")

    @override_settings(REGISTRATION_OPEN=False)
    def test_it_obeys_registration_open(self):
        r = self.client.get("/accounts/login/")
        self.assertNotContains(r, "Create Your Account")
