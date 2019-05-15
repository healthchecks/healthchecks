from datetime import timedelta as td

from django.test import Client
from django.utils.timezone import now
from hc.api.models import Check, Flip, Ping
from hc.test import BaseTestCase


class PingTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.check = Check.objects.create(project=self.project)

    def test_it_works(self):
        r = self.client.get("/ping/%s/" % self.check.code)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "up")
        expected_aa = self.check.last_ping + td(days=1, hours=1)
        self.assertEqual(self.check.alert_after, expected_aa)

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.scheme, "http")
        self.assertEqual(ping.kind, None)

    def test_it_changes_status_of_paused_check(self):
        self.check.status = "paused"
        self.check.save()

        r = self.client.get("/ping/%s/" % self.check.code)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "up")

    def test_it_clears_last_start(self):
        self.check.last_start = now()
        self.check.save()

        r = self.client.get("/ping/%s/" % self.check.code)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.last_start, None)

    def test_post_works(self):
        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.post(
            "/ping/%s/" % self.check.code, "hello world", content_type="text/plain"
        )
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.latest("id")
        self.assertEqual(ping.method, "POST")
        self.assertEqual(ping.body, "hello world")

    def test_head_works(self):
        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.head("/ping/%s/" % self.check.code)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Ping.objects.count(), 1)

    def test_it_handles_bad_uuid(self):
        r = self.client.get("/ping/not-uuid/")
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_alternative_uuid_formats(self):
        # This uuid is missing separators. uuid.UUID() would accept it.
        r = self.client.get("/ping/07c2f54898504b27af5d6c9dc157ec02/")
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_check(self):
        r = self.client.get("/ping/07c2f548-9850-4b27-af5d-6c9dc157ec02/")
        self.assertEqual(r.status_code, 404)

    def test_it_handles_120_char_ua(self):
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/44.0.2403.89 Safari/537.36"
        )

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
        r = self.client.get("/ping/%s/" % self.check.code, HTTP_X_FORWARDED_FOR=ip)
        ping = Ping.objects.latest("id")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.remote_addr, "1.1.1.1")

        ip = "1.1.1.1, 2.2.2.2"
        r = self.client.get(
            "/ping/%s/" % self.check.code,
            HTTP_X_FORWARDED_FOR=ip,
            REMOTE_ADDR="3.3.3.3",
        )
        ping = Ping.objects.latest("id")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.remote_addr, "1.1.1.1")

    def test_it_reads_forwarded_protocol(self):
        r = self.client.get(
            "/ping/%s/" % self.check.code, HTTP_X_FORWARDED_PROTO="https"
        )
        ping = Ping.objects.latest("id")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.scheme, "https")

    def test_it_never_caches(self):
        r = self.client.get("/ping/%s/" % self.check.code)
        assert "no-cache" in r.get("Cache-Control")

    def test_it_updates_confirmation_flag(self):
        payload = "Please Confirm ..."
        r = self.client.post(
            "/ping/%s/" % self.check.code, data=payload, content_type="text/plain"
        )
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.has_confirmation_link)

    def test_fail_endpoint_works(self):
        r = self.client.get("/ping/%s/fail" % self.check.code)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "down")
        self.assertEqual(self.check.alert_after, None)

        ping = Ping.objects.get()
        self.assertEqual(ping.kind, "fail")

        flip = Flip.objects.get()
        self.assertEqual(flip.owner, self.check)
        self.assertEqual(flip.new_status, "down")

    def test_start_endpoint_works(self):
        last_ping = now() - td(hours=2)
        self.check.last_ping = last_ping
        self.check.save()

        r = self.client.get("/ping/%s/start" % self.check.code)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.last_start)
        self.assertEqual(self.check.last_ping, last_ping)

        ping = Ping.objects.get()
        self.assertEqual(ping.kind, "start")

    def test_start_does_not_change_status_of_paused_check(self):
        self.check.status = "paused"
        self.check.save()

        r = self.client.get("/ping/%s/start" % self.check.code)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.last_start)
        self.assertEqual(self.check.status, "paused")
