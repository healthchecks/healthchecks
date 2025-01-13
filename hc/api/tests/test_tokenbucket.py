from __future__ import annotations

from datetime import timedelta as td

from django.test.utils import override_settings
from django.utils.timezone import now

from hc.api.models import TokenBucket
from hc.test import BaseTestCase

# This is sha1("alice@example.org" + "test-secred")
ALICE_HASH = "d60db3b2343e713a4de3e92d4eb417e4f05f06ab"


@override_settings(SECRET_KEY="test-secret")
class TokenBucketTestCase(BaseTestCase):
    def test_it_works(self) -> None:
        r = TokenBucket.authorize_login_email("alice@example.org")
        self.assertTrue(r)

        obj = TokenBucket.objects.get()
        self.assertEqual(obj.tokens, 0.95)
        self.assertEqual(obj.value, "em-" + ALICE_HASH)

    def test_it_handles_insufficient_tokens(self) -> None:
        TokenBucket.objects.create(value="em-" + ALICE_HASH, tokens=0.04)

        r = TokenBucket.authorize_login_email("alice@example.org")
        self.assertFalse(r)

    def test_it_tops_up(self) -> None:
        obj = TokenBucket(value="em-" + ALICE_HASH)
        obj.tokens = 0
        obj.updated = now() - td(minutes=30)
        obj.save()

        r = TokenBucket.authorize_login_email("alice@example.org")
        self.assertTrue(r)

        obj.refresh_from_db()
        self.assertAlmostEqual(obj.tokens, 0.45, places=4)

    def test_it_normalizes_email(self) -> None:
        emails = ("alice+alias@example.org", "a.li.ce@example.org")

        for email in emails:
            TokenBucket.authorize_login_email(email)

        self.assertEqual(TokenBucket.objects.count(), 1)

    def test_s3_get_object_healthy_works(self) -> None:
        obj = TokenBucket(value="s3_get_object_error")
        obj.tokens = 0.34  # above 1/3
        obj.updated = now()
        obj.save()
        self.assertTrue(TokenBucket.s3_is_healthy())

    def test_s3_get_object_healthy_negative_works(self) -> None:
        obj = TokenBucket(value="s3_get_object_error")
        obj.tokens = 0.1  # below 1/3
        obj.updated = now()
        obj.save()
        self.assertFalse(TokenBucket.s3_is_healthy())

    def test_record_s3_get_object_error_works(self) -> None:
        obj = TokenBucket(value="s3_get_object_error")
        obj.tokens = 0.0
        obj.updated = now()
        obj.save()

        TokenBucket.record_s3_get_object_error()
        obj.refresh_from_db()
        self.assertTrue(obj.tokens < 0)
