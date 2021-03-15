from django.test.utils import override_settings
from hc.test import BaseTestCase
from hc.accounts.models import Credential


class ProfileTestCase(BaseTestCase):
    def test_it_shows_profile_page(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Email and Password")

    def test_leaving_works(self):
        self.client.login(username="bob@example.org", password="password")

        form = {"code": str(self.project.code), "leave_project": "1"}
        r = self.client.post("/accounts/profile/", form)
        self.assertContains(r, "Left project <strong>Alices Project</strong>")
        self.assertNotContains(r, "Member")

        self.bobs_profile.refresh_from_db()
        self.assertFalse(self.bob.memberships.exists())

    def test_leaving_checks_membership(self):
        self.client.login(username="charlie@example.org", password="password")

        form = {"code": str(self.project.code), "leave_project": "1"}
        r = self.client.post("/accounts/profile/", form)
        self.assertEqual(r.status_code, 400)

    def test_it_shows_project_membership(self):
        self.client.login(username="bob@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Alices Project")
        self.assertContains(r, "Member")

    def test_it_shows_readonly_project_membership(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Alices Project")
        self.assertContains(r, "Read-only")

    def test_it_handles_no_projects(self):
        self.project.delete()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "You do not have any projects. Create one!")

    @override_settings(RP_ID=None)
    def test_it_hides_2fa_section_if_rp_id_not_set(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertNotContains(r, "Two-factor Authentication")

    @override_settings(RP_ID="testserver")
    def test_it_handles_no_credentials(self):
        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Two-factor Authentication")
        self.assertContains(r, "Your account has no registered security keys")

    @override_settings(RP_ID="testserver")
    def test_it_shows_security_key(self):
        Credential.objects.create(user=self.alice, name="Alices Key")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.get("/accounts/profile/")
        self.assertContains(r, "Alices Key")
