from django.core import mail

from hc.test import BaseTestCase
from hc.accounts.models import Member
from hc.api.models import Check
from django.conf import settings


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
        expected_subject = "Set password on %s" % settings.SITE_NAME
        self.assertEqual(mail.outbox[0].subject, expected_subject)

    def test_it_creates_api_key(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"create_api_key": "1"}
        r = self.client.post("/accounts/profile/", form)
        self.assertEqual(r.status_code, 200)

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

        form = {"invite_team_member": "1", "email": "frank@example.org"}
        r = self.client.post("/accounts/profile/", form)
        self.assertEqual(r.status_code, 200)

        member_emails = set()
        for member in self.alice.profile.member_set.all():
            member_emails.add(member.user.email)

        self.assertEqual(len(member_emails), 2)
        self.assertTrue("frank@example.org" in member_emails)

        # And an email should have been sent
        subj = ('You have been invited to join'
                ' alice@example.org on %s' % settings.SITE_NAME)
        self.assertEqual(mail.outbox[0].subject, subj)

    def test_it_checks_team_size(self):
        self.profile.team_limit = 0
        self.profile.save()

        self.client.login(username="alice@example.org", password="password")

        form = {"invite_team_member": "1", "email": "frank@example.org"}
        r = self.client.post("/accounts/profile/", form)
        self.assertEqual(r.status_code, 403)

    def test_it_removes_team_member(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"remove_team_member": "1", "email": "bob@example.org"}
        r = self.client.post("/accounts/profile/", form)
        self.assertEqual(r.status_code, 200)

        self.assertEqual(Member.objects.count(), 0)

        self.bobs_profile.refresh_from_db()
        self.assertEqual(self.bobs_profile.current_team, None)

    def test_it_sets_team_name(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"set_team_name": "1", "team_name": "Alpha Team"}
        r = self.client.post("/accounts/profile/", form)
        self.assertEqual(r.status_code, 200)

        self.alice.profile.refresh_from_db()
        self.assertEqual(self.alice.profile.team_name, "Alpha Team")

    def test_it_switches_to_own_team(self):
        self.client.login(username="bob@example.org", password="password")

        self.client.get("/accounts/profile/")

        # After visiting the profile page, team should be switched back
        # to user's default team.
        self.bobs_profile.refresh_from_db()
        self.assertEqual(self.bobs_profile.current_team, self.bobs_profile)

    def test_it_sends_change_email_link(self):
        self.client.login(username="alice@example.org", password="password")

        form = {"change_email": "1"}
        r = self.client.post("/accounts/profile/", form)
        assert r.status_code == 302

        # profile.token should be set now
        self.alice.profile.refresh_from_db()
        token = self.alice.profile.token
        self.assertTrue(len(token) > 10)

        # And an email should have been sent
        self.assertEqual(len(mail.outbox), 1)
        expected_subject = "Change email address on %s" % settings.SITE_NAME
        self.assertEqual(mail.outbox[0].subject, expected_subject)
