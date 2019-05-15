from django.core import mail

from django.conf import settings
from django.test.utils import override_settings
from hc.test import BaseTestCase
from hc.accounts.models import Member
from hc.api.models import TokenBucket


class ProjectTestCase(BaseTestCase):
    def setUp(self):
        super(ProjectTestCase, self).setUp()

        self.url = "/projects/%s/settings/" % self.project.code

    def test_it_checks_access(self):
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_allows_team_access(self):
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Change Project Name")

    def test_it_shows_api_keys(self):
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"show_api_keys": "1"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.assertContains(r, "X" * 32)
        self.assertContains(r, "R" * 32)

    def test_it_creates_api_key(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"create_api_keys": "1"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.project.refresh_from_db()
        api_key = self.project.api_key
        self.assertTrue(len(api_key) > 10)
        self.assertFalse("b'" in api_key)

    def test_it_revokes_api_key(self):
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"revoke_api_keys": "1"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.project.refresh_from_db()
        self.assertEqual(self.project.api_key, "")
        self.assertEqual(self.project.api_key_readonly, "")

    def test_it_adds_team_member(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        members = self.project.member_set.all()
        self.assertEqual(members.count(), 2)

        member = Member.objects.get(
            project=self.project, user__email="frank@example.org"
        )

        profile = member.user.profile
        self.assertEqual(profile.current_project, self.project)
        # The new user should not have their own project
        self.assertFalse(member.user.project_set.exists())

        # And an email should have been sent
        subj = (
            "You have been invited to join"
            " Alice&#39;s Project on %s" % settings.SITE_NAME
        )
        self.assertEqual(mail.outbox[0].subject, subj)

    @override_settings(SECRET_KEY="test-secret")
    def test_it_rate_limits_invites(self):
        obj = TokenBucket(value="invite-%d" % self.alice.id)
        obj.tokens = 0
        obj.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org"}
        r = self.client.post(self.url, form)
        self.assertContains(r, "Too Many Requests")

        self.assertEqual(len(mail.outbox), 0)

    def test_it_requires_owner_to_add_team_member(self):
        self.client.login(username="bob@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_checks_team_size(self):
        self.profile.team_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_removes_team_member(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"remove_team_member": "1", "email": "bob@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.assertEqual(Member.objects.count(), 0)

        self.bobs_profile.refresh_from_db()
        self.assertEqual(self.bobs_profile.current_project, None)

    def test_it_requires_owner_to_remove_team_member(self):
        self.client.login(username="bob@example.org", password="password")

        form = {"remove_team_member": "1", "email": "bob@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_checks_membership_when_removing_team_member(self):
        self.client.login(username="charlie@example.org", password="password")

        url = "/projects/%s/settings/" % self.charlies_project.code
        form = {"remove_team_member": "1", "email": "alice@example.org"}
        r = self.client.post(url, form)
        self.assertEqual(r.status_code, 400)

        self.profile.refresh_from_db()
        self.assertIsNotNone(self.profile.current_project)

    def test_it_sets_project_name(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"set_project_name": "1", "name": "Alpha Team"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Alpha Team")
