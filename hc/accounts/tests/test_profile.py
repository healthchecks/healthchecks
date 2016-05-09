from django.contrib.auth.models import User
from django.core import mail

from hc.test import BaseTestCase
from hc.accounts.models import Member
from hc.api.models import Check


class ProfileTestCase(BaseTestCase):

    def test_it_sends_set_password_link(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"set_password": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 302

        # profile.token should be set now
        self.alice.profile.refresh_from_db()
        token = self.alice.profile.token
        self.assertTrue(len(token) > 10)

        # And an email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        expected_subject = 'Set password on healthchecks.io'
        self.assertEqual(mail.outbox[0].subject, expected_subject)

    def test_it_creates_api_key(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"create_api_key": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 200

        self.alice.profile.refresh_from_db()
        api_key = self.alice.profile.api_key
        self.assertTrue(len(api_key) > 10)

    def test_it_revokes_api_key(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"revoke_api_key": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 200

        self.alice.profile.refresh_from_db()
        self.assertEqual(self.alice.profile.api_key, "")

    def test_it_sends_report(self):
        check = Check(name="Test Check", user=self.alice)
        check.save()

        self.alice.profile.send_report()

        # And an email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]

        self.assertEqual(message.subject, 'Monthly Report')
        self.assertIn("Test Check", message.body)

    def test_it_adds_team_member(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "bob@example.org"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 200

        member = self.alice.profile.member_set.get()

        self.assertEqual(member.user.email, "bob@example.org")

        # And an email should have been sent
        subj = ('You have been invited to join'
                ' alice@example.org on healthchecks.io')
        self.assertEqual(mail.outbox[0].subject, subj)

    def test_it_removes_team_member(self):
        self.client.login(username="alice@example.org", password="password")

        bob = User(username="bob", email="bob@example.org")
        bob.save()

        m = Member(team=self.alice.profile, user=bob)
        m.save()

        form = {"remove_team_member": "1", "email": "bob@example.org"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 200

        self.assertEqual(Member.objects.count(), 0)

    def test_it_sets_team_name(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"set_team_name": "1", "team_name": "Alpha Team"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 200

        self.alice.profile.refresh_from_db()
        self.assertEqual(self.alice.profile.team_name, "Alpha Team")
