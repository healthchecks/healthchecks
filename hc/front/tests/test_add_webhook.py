from hc.api.models import Channel
from hc.test import BaseTestCase


class AddWebhookTestCase(BaseTestCase):
    url = "/integrations/add_webhook/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Executes an HTTP request")

    def test_it_adds_two_webhook_urls_and_redirects(self):
        form = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "method_up": "GET",
            "url_up": "https://bar.com",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.project, self.project)
        self.assertEqual(c.down_webhook_spec["url"], "http://foo.com")
        self.assertEqual(c.up_webhook_spec["url"], "https://bar.com")

    def test_it_adds_webhook_using_team_access(self):
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
        self.assertEqual(c.down_webhook_spec["url"], "http://foo.com")
        self.assertEqual(c.up_webhook_spec["url"], "https://bar.com")

    def test_it_rejects_bad_urls(self):
        urls = [
            # clearly not an URL
            "foo",
            # FTP addresses not allowed
            "ftp://example.org",
            # no loopback
            "http://localhost:1234/endpoint",
            "http://127.0.0.1/endpoint",
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

    def test_it_handles_empty_down_url(self):
        form = {
            "method_down": "GET",
            "url_down": "",
            "method_up": "GET",
            "url_up": "http://foo.com",
        }

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.down_webhook_spec["url"], "")
        self.assertEqual(c.up_webhook_spec["url"], "http://foo.com")

    def test_it_adds_request_body(self):
        form = {
            "method_down": "POST",
            "url_down": "http://foo.com",
            "body_down": "hello",
            "method_up": "GET",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.down_webhook_spec["body"], "hello")

    def test_it_adds_headers(self):
        form = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "headers_down": "test:123\ntest2:abc",
            "method_up": "GET",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(
            c.down_webhook_spec["headers"], {"test": "123", "test2": "abc"}
        )

    def test_it_rejects_bad_headers(self):
        self.client.login(username="alice@example.org", password="password")
        form = {
            "method_down": "GET",
            "url_down": "http://example.org",
            "headers_down": "invalid-headers",
            "method_up": "GET",
        }

        r = self.client.post(self.url, form)
        self.assertContains(r, """invalid-headers""")
        self.assertEqual(Channel.objects.count(), 0)

    def test_it_strips_headers(self):
        form = {
            "method_down": "GET",
            "url_down": "http://foo.com",
            "headers_down": " test : 123 ",
            "method_up": "GET",
        }

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.down_webhook_spec["headers"], {"test": "123"})
