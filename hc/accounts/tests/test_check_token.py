from django.contrib.auth.models import User
from django.test import TestCase


class CheckTokenTestCase(TestCase):

    def test_it_redirects(self):
        alice = User(username="alice")
        alice.set_password("secret-token")
        alice.save()

        r = self.client.get("/accounts/check_token/alice/secret-token/")
        assert r.status_code == 302

        # After login, password should be unusable
        alice_again = User.objects.get(username="alice")
        assert not alice_again.has_usable_password()
