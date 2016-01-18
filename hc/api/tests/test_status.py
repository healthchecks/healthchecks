from django.test import TestCase

from hc.api.models import Check


class StatusTestCase(TestCase):

    def test_it_works(self):
        check = Check()
        check.save()

        r = self.client.get("/status/%s/" % check.code)
        self.assertContains(r, "last_ping", status_code=200)

    def test_it_handles_bad_uuid(self):
        r = self.client.get("/status/not-uuid/")
        assert r.status_code == 400
