from django.contrib.auth.models import User
from django.test import TestCase

from hc.api.models import Check


class PingTestCase(TestCase):

    def test_it_works(self):
        user = User(username="jdoe")
        user.save()

        check = Check(user=user)
        check.save()

        r = self.client.get("/ping/%s/" % check.code)
        assert r.status_code == 200

        same_check = Check.objects.get(code=check.code)
        assert same_check.status == "up"
