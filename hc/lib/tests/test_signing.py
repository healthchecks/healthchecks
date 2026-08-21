from __future__ import annotations

from unittest import TestCase

from django.core.signing import BadSignature

from hc.lib.signing import (
    HexTimestampSigner,
    ShortHexTimestampSigner,
    sign_bounce_id,
    unsign_bounce_id,
)


class SigningTestCase(TestCase):
    def test_it_works(self) -> None:
        signer = HexTimestampSigner()
        for i in range(1, 100):
            sample = "x" * i
            signed = signer.sign(sample)
            self.assertEqual(signer.unsign(signed), sample)

    def test_it_allows_lowercase(self) -> None:
        signer = HexTimestampSigner()
        signed = signer.sign("hello world").lower()
        self.assertEqual(signer.unsign(signed), "hello world")


class SignBounceIdTestCase(TestCase):
    def test_it_does_not_exceed_64_characters(self) -> None:
        # Per RFC-5321 the local-part of email addresses must not be longer
        # than 64 characters, so let's make sure that signing "n.<uuid>" does
        # not result in a string longer than 64 characters.
        signed = sign_bounce_id("n.95410c79-fcb4-4e8c-bca9-945221248211")
        self.assertTrue(len(signed) <= 64)


class UnsignBounceIdTestCase(TestCase):
    def test_it_handles_valid_hextimestampsigner_output(self) -> None:
        signed = HexTimestampSigner(sep=".", algorithm="sha1").sign("hello")
        unsign_bounce_id(signed, max_age=60)

    def test_it_handles_valid_shorthextimestampsigner_output(self) -> None:
        signed = ShortHexTimestampSigner(sep=".").sign("hello")
        unsign_bounce_id(signed, max_age=60)

    def test_it_handles_invalid_signature(self) -> None:
        signed = ShortHexTimestampSigner(sep=".").sign("hello")
        with self.assertRaises(BadSignature):
            unsign_bounce_id("a" + signed, max_age=60)
