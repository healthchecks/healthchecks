from django.test import Client, TestCase

from hc.api.models import Check, Ping


class PingTestCase(TestCase):

    def test_it_works(self):
        check = Check()
        check.save()

        r = self.client.get("/ping/%s/" % check.code)
        assert r.status_code == 200

        same_check = Check.objects.get(code=check.code)
        assert same_check.status == "up"

        pings = list(Ping.objects.all())
        assert pings[0].scheme == "http"

    def test_post_works(self):
        check = Check()
        check.save()

        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.post("/ping/%s/" % check.code)
        assert r.status_code == 200

    def test_it_handles_bad_uuid(self):
        r = self.client.get("/ping/not-uuid/")
        assert r.status_code == 400

    def test_it_handles_120_char_ua(self):
        ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/44.0.2403.89 Safari/537.36")

        check = Check()
        check.save()
        r = self.client.get("/ping/%s/" % check.code, HTTP_USER_AGENT=ua)
        assert r.status_code == 200

        pings = list(Ping.objects.all())
        assert pings[0].ua == ua

    def test_it_truncates_long_ua(self):
        ua = "01234567890" * 30

        check = Check()
        check.save()
        r = self.client.get("/ping/%s/" % check.code, HTTP_USER_AGENT=ua)
        assert r.status_code == 200

        pings = list(Ping.objects.all())
        assert len(pings[0].ua) == 200
        assert ua.startswith(pings[0].ua)
