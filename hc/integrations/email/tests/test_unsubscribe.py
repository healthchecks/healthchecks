from __future__ import annotations

import time
from unittest.mock import patch

from django.core.signing import TimestampSigner

from hc.api.models import Channel
from hc.test import BaseTestCase


class UnsubscribeEmailTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.channel = Channel(project=self.project, kind="email")
        self.channel.value = "alice@example.org"
        self.channel.save()

        signer = TimestampSigner(salt="alerts")
        signed_token = signer.sign(self.channel.make_token())
        self.url = f"/integrations/{self.channel.code}/unsub/{signed_token}/"

    def test_it_serves_confirmation_form(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(r, "Please press the button below")
        self.assertNotContains(r, "submit()")

    def test_post_unsubscribes(self) -> None:
        r = self.client.post(self.url)
        self.assertContains(r, "has been unsubscribed", status_code=200)

        q = Channel.objects.filter(code=self.channel.code)
        self.assertEqual(q.count(), 0)

    def test_fresh_signature_does_not_autosubmit(self) -> None:
        r = self.client.get(self.url)
        self.assertContains(
            r, "Please press the button below to unsubscribe", status_code=200
        )
        self.assertNotContains(r, "submit()", status_code=200)

    def test_aged_signature_does_autosubmit(self) -> None:
        with patch("django.core.signing.time") as mock_time:
            mock_time.time.return_value = time.time() - 301
            signer = TimestampSigner(salt="alerts")
            signed_token = signer.sign(self.channel.make_token())

        url = f"/integrations/{self.channel.code}/unsub/{signed_token}/"

        r = self.client.get(url)
        self.assertContains(
            r, "Please press the button below to unsubscribe", status_code=200
        )
        self.assertContains(r, "submit()", status_code=200)

    def test_it_checks_signature(self) -> None:
        signed_token = self.channel.make_token() + ":bad:signature"
        url = f"/integrations/{self.channel.code}/unsub/{signed_token}/"

        r = self.client.get(url)
        self.assertContains(r, "link you just used is incorrect", status_code=200)

    def test_it_checks_token(self) -> None:
        url = f"/integrations/{self.channel.code}/unsub/faketoken/"

        r = self.client.get(url)
        self.assertContains(r, "link you just used is incorrect", status_code=200)

    def test_it_checks_channel_kind(self) -> None:
        self.channel.kind = "webhook"
        self.channel.save()

        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 404)
