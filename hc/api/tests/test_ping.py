from django.test import Client, TestCase

from hc.api.models import Check


class PingTestCase(TestCase):

    def test_it_works(self):
        check = Check()
        check.save()

        r = self.client.get("/ping/%s/" % check.code)
        assert r.status_code == 200

        same_check = Check.objects.get(code=check.code)
        assert same_check.status == "up"

    def test_post_works(self):
        check = Check()
        check.save()

        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.post("/ping/%s/" % check.code)
        assert r.status_code == 200
