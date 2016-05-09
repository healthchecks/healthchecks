from django.contrib.auth.models import User
from django.core import mail

from hc.test import BaseTestCase
from hc.accounts.models import Profile, Member
from hc.api.models import Check


class LoginTestCase(BaseTestCase):

    def test_it_sends_set_password_link(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"set_password": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 302

        # profile.token should be set now
        profile = Profile.objects.for_user(self.alice)
        self.assertTrue(len(profile.token) > 10)

        # And an email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        expected_subject = 'Set password on healthchecks.io'
        self.assertEqual(mail.outbox[0].subject, expected_subject)

    def test_it_creates_api_key(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"create_api_key": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 200

        profile = Profile.objects.for_user(self.alice)
        self.assertTrue(len(profile.api_key) > 10)

    def test_it_revokes_api_key(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"revoke_api_key": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 200

        profile = Profile.objects.for_user(self.alice)
        self.assertEqual(profile.api_key, "")

    def test_it_sends_report(self):
        check = Check(name="Test Check", user=self.alice)
        check.save()

        profile = Profile.objects.for_user(self.alice)
        profile.send_report()

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

        profile = Profile.objects.for_user(self.alice)
        member = profile.member_set.get()

        self.assertEqual(member.user.email, "bob@example.org")

        # And an email should have been sent
        subj = ('You have been invited to join'
                ' alice@example.org on healthchecks.io')
        self.assertEqual(mail.outbox[0].subject, subj)

    def test_it_removes_team_member(self):
        self.client.login(username="alice@example.org", password="password")

        bob = User(username="bob", email="bob@example.org")
        bob.save()

        m = Member(team=Profile.objects.for_user(self.alice), user=bob)
        m.save()

        form = {"remove_team_member": "1", "email": "bob@example.org"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 200

        self.assertEqual(Member.objects.count(), 0)
