from django.core import mail

from django.conf import settings
from django.test.utils import override_settings
from hc.test import BaseTestCase
from hc.accounts.models import Member, Project
from hc.api.models import TokenBucket


class ProjectTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

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
        self.assertContains(r, "Prometheus metrics endpoint")

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

        form = {"invite_team_member": "1", "email": "frank@example.org", "rw": "1"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        members = self.project.member_set.all()
        self.assertEqual(members.count(), 2)

        member = Member.objects.get(
            project=self.project, user__email="frank@example.org"
        )

        # The read-write flag should be set
        self.assertTrue(member.rw)
        self.assertEqual(member.role, member.Role.REGULAR)

        # The new user should not have their own project
        self.assertFalse(member.user.project_set.exists())

        # And an email should have been sent
        subj = f"You have been invited to join Alices Project on {settings.SITE_NAME}"
        self.assertHTMLEqual(mail.outbox[0].subject, subj)

    def test_it_adds_readonly_team_member(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        member = Member.objects.get(
            project=self.project, user__email="frank@example.org"
        )

        self.assertFalse(member.rw)
        self.assertEqual(member.role, member.Role.READONLY)

    def test_it_adds_member_from_another_team(self):
        # With team limit at zero, we should not be able to invite any new users
        self.profile.team_limit = 0
        self.profile.save()

        # But Charlie will have an existing membership in another Alice's project
        # so Alice *should* be able to invite Charlie:
        p2 = Project.objects.create(owner=self.alice)
        Member.objects.create(user=self.charlie, project=p2)

        self.client.login(username="alice@example.org", password="password")
        form = {"invite_team_member": "1", "email": "charlie@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        q = Member.objects.filter(project=self.project, user=self.charlie)
        self.assertEqual(q.count(), 1)

        # And this should not have affected the rate limit:
        q = TokenBucket.objects.filter(value="invite-%d" % self.alice.id)
        self.assertFalse(q.exists())

    def test_it_rejects_duplicate_membership(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "bob@example.org"}
        r = self.client.post(self.url, form)
        self.assertContains(r, "bob@example.org is already a member")

        # The number of memberships should have not increased
        self.assertEqual(self.project.member_set.count(), 1)

    def test_it_rejects_owner_as_a_member(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "alice@example.org"}
        r = self.client.post(self.url, form)
        self.assertContains(r, "alice@example.org is already a member")

        # The number of memberships should have not increased
        self.assertEqual(self.project.member_set.count(), 1)

    def test_it_rejects_too_long_email_addresses(self):
        self.client.login(username="alice@example.org", password="password")

        aaa = "a" * 300
        form = {"invite_team_member": "1", "email": f"frank+{aaa}@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        # No email should have been sent
        self.assertEqual(len(mail.outbox), 0)

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

        self.assertFalse(Member.objects.exists())

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

    def test_it_sets_project_name(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"set_project_name": "1", "name": "Alpha Team"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Alpha Team")

    def test_it_shows_invite_suggestions(self):
        p2 = Project.objects.create(owner=self.alice)

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/projects/%s/settings/" % p2.code)
        self.assertContains(r, "Add Users from Other Teams")
        self.assertContains(r, "bob@example.org")

    def test_it_checks_rw_access_when_updating_project_name(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")

        form = {"set_project_name": "1", "name": "Alpha Team"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_hides_actions_for_readonly_users(self):
        self.bobs_membership.rw = False
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")

        r = self.client.get(self.url)
        self.assertNotContains(r, "#set-project-name-modal", status_code=200)
        self.assertNotContains(r, "Show API Keys")

    @override_settings(PROMETHEUS_ENABLED=False)
    def test_it_hides_prometheus_link_if_prometheus_not_enabled(self):
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"show_api_keys": "1"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.assertNotContains(r, "Prometheus metrics endpoint")
