from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from hc.api.models import Check


class LoginTestCase(TestCase):

    def test_it_sends_link(self):
        check = Check()
        check.save()

        session = self.client.session
        session["welcome_code"] = str(check.code)
        session.save()

        form = {"email": "alice@example.org"}

        r = self.client.post("/accounts/login/", form)
        assert r.status_code == 302

        # An user should have been created
        self.assertEqual(User.objects.count(), 1)

        # And email sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Log in to healthchecks.io')

        # And check should be associated with the new user
        check_again = Check.objects.get(code=check.code)
        assert check_again.user
