from __future__ import annotations

from django.test.utils import override_settings

from hc.accounts.models import Credential
from hc.test import BaseTestCase


class ProfileTestCase(BaseTestCase):
    def test_it_shows_profile_page(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Email and Password")
        self.assertContains(r, "Change Password")
        self.assertContains(r, "Set Up Authenticator App")

    def test_leaving_works(self) -> None:
        self.client.login(username="bob@example.org", password="password")

        form = {"code": str(self.project.code), "leave_project": "1"}
        r = self.client.post("/accounts/profile/", form)
        self.assertContains(r, "Left project <strong>Alices Project</strong>")
        self.assertNotContains(r, "Member")

        self.bobs_profile.refresh_from_db()
        self.assertFalse(self.bob.memberships.exists())

    def test_leaving_checks_membership(self) -> None:
        self.client.login(username="charlie@example.org", password="password")

        form = {"code": str(self.project.code), "leave_project": "1"}
        r = self.client.post("/accounts/profile/", form)
        self.assertEqual(r.status_code, 400)

    def test_it_shows_project_membership(self) -> None:
        self.client.login(username="bob@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Alices Project")
        self.assertContains(r, "Member")

    def test_it_shows_readonly_project_membership(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Alices Project")
        self.assertContains(r, "Read-only")

    def test_it_handles_no_projects(self) -> None:
        self.project.delete()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "You do not have any projects. Create one!")

    @override_settings(RP_ID=None)
    def test_it_hides_security_keys_bits_if_rp_id_not_set(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Two-factor Authentication")
        self.assertNotContains(r, "Security keys")
        self.assertNotContains(r, "Add Security Key")

    @override_settings(RP_ID="testserver")
    def test_it_handles_no_credentials(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Two-factor Authentication")
        self.assertContains(r, "Your account does not have any configured two-factor")

    @override_settings(RP_ID="testserver")
    def test_it_shows_security_key(self) -> None:
        Credential.objects.create(user=self.alice, name="Alices Key")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Alices Key")

        # It should show a warning about Alices Key being the only second factor
        s = """The key "Alices Key" is currently your only second factor."""
        self.assertContains(r, s)

    def test_it_handles_unusable_password(self) -> None:
        self.alice.set_unusable_password()
        self.alice.save()

        # Authenticate using the ProfileBackend and a token:
        token = self.profile.prepare_token()
        self.client.login(username="alice", token=token)

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Set Password")
        self.assertNotContains(r, "Change Password")

    @override_settings(RP_ID="testserver")
    def test_it_shows_totp(self) -> None:
        self.profile.totp = "0" * 32
        self.profile.totp_created = "2020-01-01T00:00:00+00:00"
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Enabled")
        self.assertContains(r, "configured on Jan 1, 2020")
        self.assertNotContains(r, "Set Up Authenticator App")

        # It should show a warning about TOTP being the only second factor
        s = "The Authenticator app is currently your only second factor."
        self.assertContains(r, s)
        self.assertContains(r, "or register a Security Key to be used")

    def test_it_shows_no_warning_if_multiple_keys_are_registered(self) -> None:
        Credential.objects.create(user=self.alice, name="Alices Key")
        Credential.objects.create(user=self.alice, name="Alices Other Key")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/")

        self.assertNotContains(r, "is currently your only second factor.")

    def test_it_shows_no_warning_if_key_and_totp_is_registered(self) -> None:
        Credential.objects.create(user=self.alice, name="Alices Key")
        self.profile.totp = "0" * 32
        self.profile.totp_created = "2020-01-01T00:00:00+00:00"
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/")

        self.assertNotContains(r, "is currently your only second factor.")

    @override_settings(RP_ID=None)
    def test_it_does_not_mention_security_key_if_rp_id_is_not_set(self) -> None:
        self.profile.totp = "0" * 32
        self.profile.totp_created = "2020-01-01T00:00:00+00:00"
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/")
        self.assertNotContains(r, "or register a Security Key to be used")
