from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.test.utils import override_settings

from hc.accounts.models import Member, Project
from hc.api.models import TokenBucket
from hc.test import BaseTestCase


class ProjectTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.url = "/projects/%s/settings/" % self.project.code

    def get_html(self, email: EmailMessage) -> str:
        assert isinstance(email, EmailMultiAlternatives)
        html, _ = email.alternatives[0]
        assert isinstance(html, str)
        return html

    def test_it_checks_access(self) -> None:
        self.client.login(username="charlie@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)

    def test_it_allows_team_access(self) -> None:
        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Change Project Name")

    def test_it_masks_keys_by_default(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.ping_key = "P" * 22
        self.project.save()

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.assertNotContains(r, "X" * 32)
        self.assertNotContains(r, "R" * 32)
        self.assertNotContains(r, "P" * 22)

    def test_it_shows_keys(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.ping_key = "P" * 22
        self.project.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"show_keys": "1"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.assertContains(r, "X" * 32)
        self.assertContains(r, "R" * 32)
        self.assertContains(r, "P" * 22)
        self.assertContains(r, "Prometheus metrics endpoint")

    def test_it_creates_readonly_key(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        form = {"create_key": "api_key_readonly"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.project.refresh_from_db()
        self.assertEqual(len(self.project.api_key_readonly), 32)
        self.assertFalse("b'" in self.project.api_key_readonly)

    def test_it_requires_rw_access_to_create_key(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {"create_key": "api_key_readonly"})
        self.assertEqual(r.status_code, 403)

    def test_it_revokes_api_key(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"revoke_key": "api_key"})
        self.assertEqual(r.status_code, 200)

        self.project.refresh_from_db()
        self.assertEqual(self.project.api_key, "")

    def test_it_requires_rw_access_to_revoke_api_key(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {"revoke_key": "api_key"})
        self.assertEqual(r.status_code, 403)

    def test_it_adds_team_member(self) -> None:
        # Use "'" in the name to see if does or doesn't get escaped in email subject:
        self.project.name = "Alice's Project"
        self.project.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "w"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        members = self.project.member_set.all()
        self.assertEqual(members.count(), 2)

        member = Member.objects.get(
            project=self.project, user__email="frank@example.org"
        )

        # The read-write flag should be set
        self.assertEqual(member.role, member.Role.REGULAR)

        # The new user should not have their own project
        self.assertFalse(member.user.project_set.exists())

        # And an email should have been sent
        message = mail.outbox[0]
        subj = f"You have been invited to join Alice's Project on {settings.SITE_NAME}"
        self.assertEqual(message.subject, subj)

        html = self.get_html(message)
        self.assertIn("You will be able to manage", message.body)
        self.assertIn("You will be able to manage", html)

    @override_settings(EMAIL_HOST=None)
    def test_it_skips_invite_email_if_email_host_not_set(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "w"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.assertEqual(self.project.member_set.count(), 2)
        self.assertEqual(len(mail.outbox), 0)

    def test_it_adds_readonly_team_member(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "r"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        member = Member.objects.get(
            project=self.project, user__email="frank@example.org"
        )

        self.assertEqual(member.role, member.Role.READONLY)

        # And an email should have been sent
        message = mail.outbox[0]
        html = self.get_html(message)
        self.assertIn("You will be able to view", message.body)
        self.assertIn("You will be able to view", html)

    def test_it_adds_manager_team_member(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "m"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        member = Member.objects.get(
            project=self.project, user__email="frank@example.org"
        )

        # The new user should have role manager
        self.assertEqual(member.role, member.Role.MANAGER)

    def test_it_adds_member_from_another_team(self) -> None:
        # With team limit at zero, we should not be able to invite any new users
        self.profile.team_limit = 0
        self.profile.save()

        # But Charlie will have an existing membership in another Alice's project
        # so Alice *should* be able to invite Charlie:
        p2 = Project.objects.create(owner=self.alice)
        Member.objects.create(user=self.charlie, project=p2)

        self.client.login(username="alice@example.org", password="password")
        form = {"invite_team_member": "1", "email": "charlie@example.org", "role": "r"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        q = Member.objects.filter(project=self.project, user=self.charlie)
        self.assertEqual(q.count(), 1)

        # And this should not have affected the rate limit:
        tq = TokenBucket.objects.filter(value="invite-%d" % self.alice.id)
        self.assertFalse(tq.exists())

    def test_it_rejects_duplicate_membership(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "bob@example.org", "role": "r"}
        r = self.client.post(self.url, form)
        self.assertContains(r, "bob@example.org is already a member")

        # The number of memberships should have not increased
        self.assertEqual(self.project.member_set.count(), 1)

    def test_it_rejects_owner_as_a_member(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "alice@example.org", "role": "r"}
        r = self.client.post(self.url, form)
        self.assertContains(r, "alice@example.org is already a member")

        # The number of memberships should have not increased
        self.assertEqual(self.project.member_set.count(), 1)

    def test_it_rejects_too_long_email_addresses(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        aaa = "a" * 300
        form = {
            "invite_team_member": "1",
            "email": f"frank+{aaa}@example.org",
            "role": "r",
        }
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        # No email should have been sent
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(SECRET_KEY="test-secret")
    def test_it_rate_limits_invites(self) -> None:
        obj = TokenBucket(value="invite-%d" % self.alice.id)
        obj.tokens = 0
        obj.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "r"}
        r = self.client.post(self.url, form)
        self.assertContains(r, "Too Many Requests")

        self.assertEqual(len(mail.outbox), 0)

    def test_it_lets_manager_add_team_member(self) -> None:
        # Bob is a manager:
        self.bobs_membership.role = "m"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "w"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        Member.objects.get(project=self.project, user__email="frank@example.org")

    def test_it_does_not_allow_regular_member_invite_team_members(self) -> None:
        self.client.login(username="bob@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "w"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_checks_team_size(self) -> None:
        self.profile.team_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "r"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_invites_user_with_email_as_username(self) -> None:
        User.objects.create(username="frank@example.org", email="frank@example.org")

        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org", "role": "w"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        q = Member.objects.filter(project=self.project, user__email="frank@example.org")
        self.assertEqual(q.count(), 1)

    def test_it_lets_owner_remove_team_member(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        form = {"remove_team_member": "1", "email": "bob@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.assertFalse(Member.objects.exists())

    def test_it_lets_manager_remove_team_member(self) -> None:
        # Bob is a manager:
        self.bobs_membership.role = "m"
        self.bobs_membership.save()

        # Bob will try to remove this membership:
        Member.objects.create(user=self.charlie, project=self.project)

        self.client.login(username="bob@example.org", password="password")
        form = {"remove_team_member": "1", "email": "charlie@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        q = Member.objects.filter(user=self.charlie, project=self.project)
        self.assertFalse(q.exists())

    def test_it_does_not_allow_regular_member_remove_team_member(self) -> None:
        # Bob will try to remove this membership:
        Member.objects.create(user=self.charlie, project=self.project)

        self.client.login(username="bob@example.org", password="password")
        form = {"remove_team_member": "1", "email": "charlie@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_rejects_manager_remove_self(self) -> None:
        self.bobs_membership.role = "m"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")

        form = {"remove_team_member": "1", "email": "bob@example.org"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 400)

        # The number of memberships should have not decreased
        self.assertEqual(self.project.member_set.count(), 1)

    def test_it_checks_membership_when_removing_team_member(self) -> None:
        self.client.login(username="charlie@example.org", password="password")

        url = "/projects/%s/settings/" % self.charlies_project.code
        form = {"remove_team_member": "1", "email": "alice@example.org"}
        r = self.client.post(url, form)
        self.assertEqual(r.status_code, 400)

    def test_it_sets_project_name(self) -> None:
        self.client.login(username="alice@example.org", password="password")

        form = {"set_project_name": "1", "name": "Alpha Team"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 200)

        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Alpha Team")

    def test_it_requires_rw_access_to_set_project_name(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        form = {"set_project_name": "1", "name": "Alpha Team"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_shows_invite_suggestions(self) -> None:
        p2 = Project.objects.create(owner=self.alice)

        self.client.login(username="alice@example.org", password="password")

        r = self.client.get("/projects/%s/settings/" % p2.code)
        self.assertContains(r, "Add Users from Other Projects")
        self.assertContains(r, "bob@example.org")

    def test_it_requires_rw_access_to_update_project_name(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")

        form = {"set_project_name": "1", "name": "Alpha Team"}
        r = self.client.post(self.url, form)
        self.assertEqual(r.status_code, 403)

    def test_it_hides_actions_for_readonly_users(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")

        r = self.client.get(self.url)
        self.assertNotContains(r, "#set-project-name-modal", status_code=200)
        self.assertNotContains(r, "Show API Keys")

    @override_settings(PROMETHEUS_ENABLED=False)
    def test_it_hides_prometheus_link_if_prometheus_not_enabled(self) -> None:
        self.project.api_key_readonly = "R" * 32
        self.project.save()

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, {"show_api_keys": "1"})
        self.assertEqual(r.status_code, 200)

        self.assertNotContains(r, "Prometheus metrics endpoint")

    def test_it_requires_rw_access_to_show_api_key(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.post(self.url, {"show_keys": "1"})
        self.assertEqual(r.status_code, 403)
