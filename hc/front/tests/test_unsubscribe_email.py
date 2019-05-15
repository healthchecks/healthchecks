from hc.api.models import Channel
from hc.test import BaseTestCase


class UnsubscribeEmailTestCase(BaseTestCase):
    def setUp(self):
        super(UnsubscribeEmailTestCase, self).setUp()
        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

    def test_it_works(self):
        token = self.channel.make_token()
        url = "/integrations/%s/unsub/%s/" % (self.channel.code, token)

        r = self.client.get(url)
        self.assertContains(r, "has been unsubscribed", status_code=200)

        q = Channel.objects.filter(code=self.channel.code)
        self.assertEqual(q.count(), 0)

    def test_it_checks_token(self):
        url = "/integrations/%s/unsub/faketoken/" % self.channel.code

        r = self.client.get(url)
        self.assertContains(r, "link you just used is incorrect", status_code=200)

    def test_it_checks_channel_kind(self):
        self.channel.kind = "webhook"
        self.channel.save()

        token = self.channel.make_token()
        url = "/integrations/%s/unsub/%s/" % (self.channel.code, token)

        r = self.client.get(url)
        self.assertEqual(r.status_code, 400)

    def test_post_works(self):
        token = self.channel.make_token()
        url = "/integrations/%s/unsub/%s/" % (self.channel.code, token)

        r = self.client.post(url)
        self.assertContains(r, "has been unsubscribed", status_code=200)

    def test_it_serves_confirmation_form(self):
        token = self.channel.make_token()
        url = "/integrations/%s/unsub/%s/?ask=1" % (self.channel.code, token)

        r = self.client.get(url)
        self.assertContains(r, "Please press the button below")
