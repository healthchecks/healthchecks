from django.test import Client, TestCase

from hc.api.models import Check, Ping


class PingTestCase(TestCase):

    def setUp(self):
        super(PingTestCase, self).setUp()
        self.check = Check.objects.create()

    def test_it_works(self):
        r = self.client.get("/ping/%s/" % self.check.code)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "up")
        self.assertEqual(self.check.alert_after, self.check.get_alert_after())

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "http")

    def test_it_changes_status_of_paused_check(self):
        self.check.status = "paused"
        self.check.save()

        r = self.client.get("/ping/%s/" % self.check.code)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "up")

    def test_post_works(self):
        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.post("/ping/%s/" % self.check.code, "hello world",
                             content_type="text/plain")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.last_ping_body, "hello world")

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.method, "POST")

    def test_head_works(self):
        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.head("/ping/%s/" % self.check.code)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Ping.objects.count(), 1)

    def test_it_handles_bad_uuid(self):
        r = self.client.get("/ping/not-uuid/")
        self.assertEqual(r.status_code, 400)

    def test_it_rejects_alternative_uuid_formats(self):
        # This uuid is missing separators. uuid.UUID() would accept it.
        r = self.client.get("/ping/07c2f54898504b27af5d6c9dc157ec02/")
        self.assertEqual(r.status_code, 400)

    def test_it_handles_missing_check(self):
        r = self.client.get("/ping/07c2f548-9850-4b27-af5d-6c9dc157ec02/")
        self.assertEqual(r.status_code, 404)

    def test_it_handles_120_char_ua(self):
        ua = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) "
              "AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/44.0.2403.89 Safari/537.36")

        r = self.client.get("/ping/%s/" % self.check.code, HTTP_USER_AGENT=ua)
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.ua, ua)

    def test_it_truncates_long_ua(self):
        ua = "01234567890" * 30

        r = self.client.get("/ping/%s/" % self.check.code, HTTP_USER_AGENT=ua)
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.latest("id")
        self.assertEqual(len(ping.ua), 200)
        assert ua.startswith(ping.ua)

    def test_it_reads_forwarded_ip(self):
        ip = "1.1.1.1"
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_FOR=ip)
        ping = Ping.objects.latest("id")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.remote_addr, "1.1.1.1")

        ip = "1.1.1.1, 2.2.2.2"
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_FOR=ip, REMOTE_ADDR="3.3.3.3")
        ping = Ping.objects.latest("id")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.remote_addr, "1.1.1.1")

    def test_it_reads_forwarded_protocol(self):
        r = self.client.get("/ping/%s/" % self.check.code,
                            HTTP_X_FORWARDED_PROTO="https")
        ping = Ping.objects.latest("id")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.scheme, "https")

    def test_it_never_caches(self):
        r = self.client.get("/ping/%s/" % self.check.code)
        assert "no-cache" in r.get("Cache-Control")
