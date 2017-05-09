from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class LastPingTestCase(BaseTestCase):

    def test_it_works(self):
        check = Check(user=self.alice)
        check.last_ping_body = "this is body"
        check.save()

        Ping.objects.create(owner=check)

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/checks/%s/last_ping/" % check.code)
        self.assertContains(r, "this is body", status_code=200)

    def test_it_requires_user(self):
        check = Check.objects.create()
        r = self.client.post("/checks/%s/last_ping/" % check.code)
        self.assertEqual(r.status_code, 403)
