from __future__ import annotations

from django.test.utils import override_settings

from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class AddWebhookTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.check = Check.objects.create(project=self.project)
        self.url = f"/projects/{self.project.code}/add_webhook/"

    def test_instructions_work(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Executes an HTTP request")

    def test_it_saves_name(self) -> None:
        form = {
            "name": "Call foo.com",
            "method_down": "GET",
            "url_down": "http://foo.com",
            "method_up": "GET",
            "url_up": "",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.name, "Call foo.com")

        # Make sure it calls assign_all_checks
        self.assertEqual(c.checks.count(), 1)

    def test_it_adds_two_webhook_urls_and_redirects(self) -> None:
        form = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "method_up": "GET",
            "url_up": "https://bar.com",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.project, self.project)
        self.assertEqual(c.down_webhook_spec.url, "http://foo.com")
        self.assertEqual(c.up_webhook_spec.url, "https://bar.com")

    def test_it_adds_webhook_using_team_access(self) -> None:
        form = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "method_up": "GET",
            "url_up": "https://bar.com",
        }

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.project, self.project)
        self.assertEqual(c.down_webhook_spec.url, "http://foo.com")
        self.assertEqual(c.up_webhook_spec.url, "https://bar.com")

    def test_it_accepts_good_urls(self) -> None:
        urls = [
            "http://foo",
            "http://localhost:1234/a",
            "http://127.0.0.1/a",
            "http://user:pass@example.org:80",
            "http://user:pass@example:80",
            "http://example.com.",
        ]

        self.client.login(username="alice@example.org", password="password")
        for url in urls:
            form = {
                "method_down": "GET",
                "url_down": url,
                "method_up": "GET",
                "url_up": "",
            }
            r = self.client.post(self.url, form)
            self.assertRedirects(r, self.channels_url, msg_prefix=url)

    def test_it_rejects_bad_urls(self) -> None:
        urls = [
            # clearly not an URL
            "foo bar",
            # FTP addresses not allowed
            "ftp://example.org",
            "http://example:80.com/",
        ]

        self.client.login(username="alice@example.org", password="password")
        for url in urls:
            form = {
                "method_down": "GET",
                "url_down": url,
                "method_up": "GET",
                "url_up": "",
            }

            r = self.client.post(self.url, form)
            self.assertContains(r, "Enter a valid URL.", msg_prefix=url)

            self.assertEqual(Channel.objects.count(), 0)

    def test_it_handles_empty_down_url(self) -> None:
        form = {
            "method_down": "GET",
            "url_down": "",
            "method_up": "GET",
            "url_up": "http://foo.com",
        }

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.down_webhook_spec.url, "")
        self.assertEqual(c.up_webhook_spec.url, "http://foo.com")

    def test_it_adds_request_body(self) -> None:
        form = {
            "method_down": "POST",
            "url_down": "http://foo.com",
            "body_down": "hello",
            "method_up": "GET",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.down_webhook_spec.body, "hello")

    def test_it_adds_headers(self) -> None:
        form = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "headers_down": "test:123\ntest2:abc",
            "method_up": "GET",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.down_webhook_spec.headers, {"test": "123", "test2": "abc"})

    def test_it_rejects_bad_headers(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        form = {
            "method_down": "GET",
            "url_down": "http://example.org",
            "headers_down": "invalid-header\nfoo:bar",
            "method_up": "GET",
        }

        r = self.client.post(self.url, form)
        self.assertContains(r, """invalid-header""")
        self.assertEqual(Channel.objects.count(), 0)

    def test_it_rejects_non_latin1_in_header_name(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        form = {
            "method_down": "GET",
            "url_down": "http://example.org",
            "headers_down": "fō:bar",
            "method_up": "GET",
        }

        r = self.client.post(self.url, form)
        self.assertContains(r, """must not contain special characters""")
        self.assertEqual(Channel.objects.count(), 0)

    def test_it_strips_headers(self) -> None:
        form = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "headers_down": " test : 123 ",
            "method_up": "GET",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, self.channels_url)

        c = Channel.objects.get()
        self.assertEqual(c.down_webhook_spec.headers, {"test": "123"})

    def test_it_rejects_both_empty(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        form = {
            "method_down": "GET",
            "url_down": "",
            "method_up": "GET",
            "url_up": "",
        }

        r = self.client.post(self.url, form)
        self.assertContains(r, "Enter a valid URL.")

        self.assertEqual(Channel.objects.count(), 0)

    def test_it_requires_rw_access(self) -> None:
        self.bobs_membership.role = "r"
        self.bobs_membership.save()

        self.client.login(username="bob@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 403)

    @override_settings(WEBHOOKS_ENABLED=False)
    def test_it_handles_disabled_integration(self) -> None:
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
