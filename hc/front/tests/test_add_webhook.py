from hc.api.models import Channel
from hc.test import BaseTestCase


class AddWebhookTestCase(BaseTestCase):
    url = "/integrations/add_webhook/"

    def test_instructions_work(self):
        self.client.login(username="alice@example.org", password="password")
        r = self.client.get(self.url)
        self.assertContains(r, "Runs a HTTP GET or HTTP POST")

    def test_it_adds_two_webhook_urls_and_redirects(self):
        form = {"url_down": "http://foo.com", "url_up": "https://bar.com"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.value, '{"headers": {}, "post_data": "", "url_down": "http://foo.com", "url_up": "https://bar.com"}')

    def test_it_adds_webhook_using_team_access(self):
        form = {"url_down": "http://foo.com", "url_up": "https://bar.com"}

        # Logging in as bob, not alice. Bob has team access so this
        # should work.
        self.client.login(username="bob@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.user, self.alice)
        self.assertEqual(c.value, '{"headers": {}, "post_data": "", "url_down": "http://foo.com", "url_up": "https://bar.com"}')

    def test_it_rejects_bad_urls(self):
        urls = [
            # clearly not an URL
            "foo",
            # FTP addresses not allowed
            "ftp://example.org",
            # no loopback
            "http://localhost:1234/endpoint",
            "http://127.0.0.1/endpoint"
        ]

        self.client.login(username="alice@example.org", password="password")
        for url in urls:
            form = {"url_down": url, "url_up": ""}

            r = self.client.post(self.url, form)
            self.assertContains(r, "Enter a valid URL.", msg_prefix=url)

            self.assertEqual(Channel.objects.count(), 0)

    def test_it_handles_empty_down_url(self):
        form = {"url_down": "", "url_up": "http://foo.com"}

        self.client.login(username="alice@example.org", password="password")
        self.client.post(self.url, form)

        c = Channel.objects.get()
        self.assertEqual(c.value, '{"headers": {}, "post_data": "", "url_down": "", "url_up": "http://foo.com"}')

    def test_it_adds_post_data(self):
        form = {"url_down": "http://foo.com", "post_data": "hello"}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.value, '{"headers": {}, "post_data": "hello", "url_down": "http://foo.com", "url_up": ""}')

    def test_it_adds_headers(self):
        form = {"url_down": "http://foo.com", "header_key[]": ["test", "test2"], "header_value[]": ["123", "abc"]}

        self.client.login(username="alice@example.org", password="password")
        r = self.client.post(self.url, form)
        self.assertRedirects(r, "/integrations/")

        c = Channel.objects.get()
        self.assertEqual(c.value, '{"headers": {"test": "123", "test2": "abc"}, "post_data": "", "url_down": "http://foo.com", "url_up": ""}')

