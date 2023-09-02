from __future__ import annotations

from datetime import timedelta as td
from unittest.mock import Mock, patch
from uuid import uuid4

from django.test import Client
from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import Check, Flip, Ping
from hc.test import BaseTestCase


@override_settings(S3_BUCKET=None)
class PingTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/ping/{self.check.code}"
        self.project.api_key = "X" * 32

    @override_settings(PING_BODY_LIMIT=10000)
    def test_it_works(self) -> None:
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "*")
        self.assertEqual(r.headers["Ping-Body-Limit"], "10000")

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "up")
        assert self.check.last_ping
        expected_aa = self.check.last_ping + td(days=1, hours=1)
        self.assertEqual(self.check.alert_after, expected_aa)

        ping = Ping.objects.get()
        self.assertEqual(ping.scheme, "http")
        self.assertEqual(ping.kind, None)
        self.assertEqual(ping.created, self.check.last_ping)
        self.assertIsNone(ping.exitstatus)

    def test_it_changes_status_of_paused_check(self) -> None:
        self.check.status = "paused"
        self.check.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "up")

    def test_it_clears_last_start(self) -> None:
        self.check.last_start = now()
        self.check.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.last_start, None)

    def test_post_works(self) -> None:
        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.post(self.url, "hello world", content_type="text/plain")
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.get()
        self.assertEqual(ping.method, "POST")
        assert ping.body_raw
        self.assertEqual(bytes(ping.body_raw), b"hello world")

    def test_head_works(self) -> None:
        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.head(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Ping.objects.count(), 1)

    def test_it_handles_bad_uuid(self) -> None:
        r = self.client.get("/ping/not-uuid/")
        self.assertEqual(r.status_code, 404)

    def test_it_rejects_alternative_uuid_formats(self) -> None:
        # This uuid is missing separators. uuid.UUID() would accept it.
        r = self.client.get("/ping/07c2f54898504b27af5d6c9dc157ec02/")
        self.assertEqual(r.status_code, 404)

    def test_it_handles_missing_check(self) -> None:
        r = self.client.get("/ping/07c2f548-9850-4b27-af5d-6c9dc157ec02/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.content.decode(), "not found")

    def test_it_handles_120_char_ua(self) -> None:
        ua = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_4) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/44.0.2403.89 Safari/537.36"
        )

        r = self.client.get(self.url, HTTP_USER_AGENT=ua)
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.get()
        self.assertEqual(ping.ua, ua)

    def test_it_truncates_long_ua(self) -> None:
        ua = "01234567890" * 30

        r = self.client.get(self.url, HTTP_USER_AGENT=ua)
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.get()
        self.assertEqual(len(ping.ua), 200)
        assert ua.startswith(ping.ua)

    def test_it_reads_forwarded_ip(self) -> None:
        ip = "1.1.1.1"
        r = self.client.get(self.url, HTTP_X_FORWARDED_FOR=ip)
        ping = Ping.objects.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.remote_addr, "1.1.1.1")

    def test_it_reads_forwarded_ipv6_ip(self) -> None:
        ip = "2001::1"
        r = self.client.get(self.url, HTTP_X_FORWARDED_FOR=ip)
        ping = Ping.objects.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.remote_addr, "2001::1")

    def test_it_reads_first_forwarded_ip(self) -> None:
        ip = "1.1.1.1, 2.2.2.2"
        r = self.client.get(
            self.url,
            HTTP_X_FORWARDED_FOR=ip,
            REMOTE_ADDR="3.3.3.3",
        )
        ping = Ping.objects.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.remote_addr, "1.1.1.1")

    def test_it_handles_forwarded_ip_plus_port(self) -> None:
        ip = "1.1.1.1:1234"
        r = self.client.get(
            self.url,
            HTTP_X_FORWARDED_FOR=ip,
            REMOTE_ADDR="3.3.3.3",
        )
        ping = Ping.objects.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.remote_addr, "1.1.1.1")

    def test_it_reads_forwarded_protocol(self) -> None:
        r = self.client.get(self.url, HTTP_X_FORWARDED_PROTO="https")
        ping = Ping.objects.get()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(ping.scheme, "https")

    def test_it_never_caches(self) -> None:
        r = self.client.get(self.url)
        assert "no-cache" in r["Cache-Control"]

    def test_it_updates_confirmation_flag(self) -> None:
        payload = "Please Confirm ..."
        r = self.client.post(self.url, data=payload, content_type="text/plain")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.has_confirmation_link)

    def test_fail_endpoint_works(self) -> None:
        r = self.client.get(self.url + "/fail")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "down")
        self.assertEqual(self.check.alert_after, None)

        ping = Ping.objects.get()
        self.assertEqual(ping.kind, "fail")

        flip = Flip.objects.get()
        self.assertEqual(flip.owner, self.check)
        self.assertEqual(flip.new_status, "down")

    def test_start_endpoint_works(self) -> None:
        last_ping = now() - td(hours=2)
        self.check.last_ping = last_ping
        self.check.save()

        r = self.client.get(self.url + "/start")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.last_start)
        self.assertEqual(self.check.last_ping, last_ping)

        ping = Ping.objects.get()
        self.assertEqual(ping.kind, "start")

    def test_start_does_not_change_status_of_paused_check(self) -> None:
        self.check.status = "paused"
        self.check.save()

        r = self.client.get(self.url + "/start")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.last_start)
        self.assertEqual(self.check.status, "paused")

    def test_start_sets_last_start_rid(self) -> None:
        rid = uuid4()
        r = self.client.get(self.url + f"/start?rid={rid}")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertTrue(self.check.last_start)
        self.assertEqual(self.check.last_start_rid, rid)

    def test_it_sets_last_duration(self) -> None:
        self.check.last_start = now() - td(seconds=10)
        self.check.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        assert self.check.last_duration
        self.assertTrue(self.check.last_duration.total_seconds() >= 10)

    def test_it_does_not_update_last_ping_on_rid_mismatch(self) -> None:
        t = now() - td(seconds=10)
        self.check.last_start = t
        self.check.last_start_rid = uuid4()
        self.check.save()

        r = self.client.get(self.url + f"?rid={uuid4()}")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        # last_start should still be the same
        self.assertEqual(self.check.last_start, t)
        # last_duration should be not set
        self.assertIsNone(self.check.last_duration)

    def test_it_clears_last_ping_and_sets_last_duration_if_rid_matches(self) -> None:
        self.check.last_start = now() - td(seconds=10)
        self.check.last_start_rid = uuid4()
        self.check.save()

        r = self.client.get(self.url + f"?rid={self.check.last_start_rid}")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertIsNone(self.check.last_start)
        assert self.check.last_duration
        self.assertTrue(self.check.last_duration.total_seconds() >= 10)

    def test_it_clears_last_ping_if_rid_is_absent(self) -> None:
        self.check.last_start = now() - td(seconds=10)
        self.check.last_start_rid = uuid4()
        self.check.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertIsNone(self.check.last_start)
        self.assertIsNone(self.check.last_duration)

    def test_it_clears_last_ping_on_failure(self) -> None:
        self.check.last_start = now() - td(seconds=10)
        self.check.last_start_rid = uuid4()
        self.check.save()

        r = self.client.get(self.url + f"/fail?rid={uuid4()}")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertIsNone(self.check.last_start)
        self.assertIsNone(self.check.last_duration)

    def test_it_requires_post(self) -> None:
        self.check.methods = "POST"
        self.check.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "new")
        self.assertIsNone(self.check.last_ping)

        ping = Ping.objects.get()
        self.assertEqual(ping.scheme, "http")
        self.assertEqual(ping.kind, "ign")

    @override_settings(PING_BODY_LIMIT=5)
    def test_it_chops_long_body(self) -> None:
        r = self.client.post(self.url, "hello world", content_type="text/plain")
        self.assertEqual(r.headers["Ping-Body-Limit"], "5")

        ping = Ping.objects.get()
        self.assertEqual(ping.method, "POST")
        assert ping.body_raw
        self.assertEqual(bytes(ping.body_raw), b"hello")

    @override_settings(PING_BODY_LIMIT=None)
    def test_it_allows_unlimited_body(self) -> None:
        r = self.client.post(self.url, "A" * 20000, content_type="text/plain")
        self.assertNotIn("Ping-Body-Limit", r.headers)

        ping = Ping.objects.get()
        assert ping.body_raw
        self.assertEqual(len(ping.body_raw), 20000)

    def test_it_handles_manual_resume_flag(self) -> None:
        self.check.status = "paused"
        self.check.manual_resume = True
        self.check.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "paused")

        ping = Ping.objects.get()
        self.assertEqual(ping.scheme, "http")
        self.assertEqual(ping.kind, "ign")

    def test_zero_exit_status_works(self) -> None:
        r = self.client.get(self.url + "/0")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "up")

        ping = Ping.objects.get()
        self.assertEqual(ping.kind, None)
        self.assertEqual(ping.exitstatus, 0)

    def test_nonzero_exit_status_works(self) -> None:
        r = self.client.get(self.url + "/123")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "down")

        ping = Ping.objects.get()
        self.assertEqual(ping.kind, "fail")
        self.assertEqual(ping.exitstatus, 123)

    def test_it_rejects_exit_status_over_255(self) -> None:
        r = self.client.get(self.url + "/256")
        self.assertEqual(r.status_code, 400)

    def test_it_accepts_bad_unicode(self) -> None:
        csrf_client = Client(enforce_csrf_checks=True)
        r = csrf_client.post(self.url, b"Hello \xe9 World", content_type="text/plain")
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.get()
        self.assertEqual(ping.method, "POST")
        assert ping.body_raw
        self.assertEqual(bytes(ping.body_raw), b"Hello \xe9 World")

    @override_settings(S3_BUCKET="test-bucket", PING_BODY_LIMIT=None)
    @patch("hc.api.models.put_object")
    def test_it_uploads_body_to_s3(self, put_object: Mock) -> None:
        r = self.client.post(self.url, b"a" * 101, content_type="text/plain")
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.get()
        self.assertEqual(ping.method, "POST")
        self.assertEqual(ping.object_size, 101)

        code, n, data = put_object.call_args.args
        self.assertEqual(code, self.check.code)
        self.assertEqual(n, 1)
        self.assertEqual(data, b"a" * 101)

    def test_log_endpoint_works(self) -> None:
        r = self.client.post(self.url + "/log", "hello", content_type="text/plain")
        self.assertEqual(r.status_code, 200)

        self.check.refresh_from_db()
        self.assertEqual(self.check.status, "new")
        self.assertIsNone(self.check.alert_after)
        self.assertFalse(self.check.last_ping)

        ping = Ping.objects.get()
        self.assertEqual(ping.kind, "log")
        assert ping.body_raw
        self.assertEqual(bytes(ping.body_raw), b"hello")

        self.assertFalse(Flip.objects.exists())

    def test_it_saves_run_id(self) -> None:
        rid = uuid4()
        r = self.client.get(self.url + f"/start?rid={rid}")
        self.assertEqual(r.status_code, 200)

        ping = Ping.objects.get()
        self.assertEqual(ping.rid, rid)

    def test_it_handles_invalid_rid(self) -> None:
        samples = ["12345", "684e2e73-017e-465f-8149-d70b7c5aaa490"]
        for sample in samples:
            r = self.client.get(self.url + f"/start?rid={sample}")
            self.assertEqual(r.status_code, 400)
