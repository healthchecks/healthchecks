from hc.api.models import Check, Ping
from hc.test import BaseTestCase


class LastPingTestCase(BaseTestCase):

    def test_it_works(self):
        check = Check(user=self.alice)
        check.save()

        Ping.objects.create(owner=check, body="this is body")

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post("/checks/%s/last_ping/" % check.code)
        self.assertContains(r, "this is body", status_code=200)

    def test_it_requires_user(self):
        check = Check.objects.create()
        r = self.client.post("/checks/%s/last_ping/" % check.code)
        self.assertEqual(r.status_code, 403)

    def test_it_accepts_n(self):
        check = Check(user=self.alice)
        check.save()

        # remote_addr, scheme, method, ua, body:
        check.ping("1.2.3.4", "http", "post", "tester", "foo-123")
        check.ping("1.2.3.4", "http", "post", "tester", "bar-456")

        self.client.login(username="alice@example.org", password="password")

        r = self.client.post("/checks/%s/pings/1/" % check.code)
        self.assertContains(r, "foo-123", status_code=200)

        r = self.client.post("/checks/%s/pings/2/" % check.code)
        self.assertContains(r, "bar-456", status_code=200)
