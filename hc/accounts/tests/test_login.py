from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from hc.api.models import Check
from django.conf import settings

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
        self.assertEqual(mail.outbox[0].subject, 'Log in to {0}'.format(getattr(settings, "SITE_NAME")))

        # And check should be associated with the new user
        check_again = Check.objects.get(code=check.code)
        assert check_again.user

    def test_it_pops_bad_link_from_session(self):
        self.client.session["bad_link"] = True
        self.client.get("/accounts/login/")
        assert "bad_link" not in self.client.session
