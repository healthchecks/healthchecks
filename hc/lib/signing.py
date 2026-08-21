from __future__ import annotations

import time

from django.core.signing import BadSignature, SignatureExpired, Signer
from django.utils.crypto import salted_hmac


def hex_hmac(salt: str, value: bytes | str, key: bytes | str, algorithm: str) -> str:
    return salted_hmac(salt, value, key, algorithm=algorithm).hexdigest()


class HexTimestampSigner(Signer):
    """TimestampSigner, but uses hex for serialization."""

    def signature(self, value: bytes | str, key: bytes | str | None = None) -> str:
        key = key or self.key
        assert isinstance(self.salt, str)
        return hex_hmac(self.salt + "signer", value, key, algorithm=self.algorithm)

    def sign(self, value: str) -> str:
        timestamp = hex(int(time.time()))[2:]
        value = f"{value}{self.sep}{timestamp}"
        return super().sign(value)

    def unsign(self, value: str, max_age: int | None = None) -> str:
        result = super().unsign(value)
        value, timestamp_str = result.rsplit(self.sep, 1)
        timestamp = int(timestamp_str, base=16)
        if max_age is not None:
            age = time.time() - timestamp
            if age > max_age:
                raise SignatureExpired(f"Signature age {age} > {max_age} seconds")
        return value


class ShortHexTimestampSigner(Signer):
    """TimestampSigner, but uses hex for serialization, and uses a short signature."""

    def signature(self, value: bytes | str, key: bytes | str | None = None) -> str:
        key = key or self.key
        assert isinstance(self.salt, str)
        full = hex_hmac(self.salt + "signer", value, key, algorithm=self.algorithm)
        # Chop off the end of the signature. This makes the signature weaker
        # but that's acceptable for our intended use case, signing bounce notifications.
        # The goal is to make a signed "n.<uuid>" or "r.<uuid>" string fit in
        # 64 characters so it can be used in the local-part of an email address.
        return full[:16]

    def sign(self, value: str) -> str:
        timestamp = hex(int(time.time()))[2:]
        value = f"{value}{self.sep}{timestamp}"
        return super().sign(value)

    def unsign(self, value: str, max_age: int | None = None) -> str:
        result = super().unsign(value)
        value, timestamp_str = result.rsplit(self.sep, 1)
        timestamp = int(timestamp_str, base=16)
        if max_age is not None:
            age = time.time() - timestamp
            if age > max_age:
                raise SignatureExpired(f"Signature age {age} > {max_age} seconds")
        return value


def sign_bounce_id(s: str) -> str:
    return ShortHexTimestampSigner(sep=".").sign(s)


def unsign_bounce_id(s: str, max_age: int) -> str:
    try:
        hex_signer = HexTimestampSigner(sep=".", algorithm="sha1")
        return hex_signer.unsign(s, max_age=max_age)
    except BadSignature:
        short_hex_signer = ShortHexTimestampSigner(sep=".")
        return short_hex_signer.unsign(s, max_age=max_age)
