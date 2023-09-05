from __future__ import annotations

from unittest import TestCase

from hc.lib.signing import HexTimestampSigner


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
