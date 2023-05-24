from __future__ import annotations

import time

from django.core.signing import SignatureExpired, Signer
from django.utils.crypto import salted_hmac


def hex_hmac(salt, value, key, algorithm):
    return salted_hmac(salt, value, key, algorithm=algorithm).hexdigest()


class HexTimestampSigner(Signer):
    """TimestampSigner, but uses hex for serialization."""

    def signature(self, value, key=None):
        key = key or self.key
        return hex_hmac(self.salt + "signer", value, key, algorithm=self.algorithm)

    def sign(self, value):
        timestamp = hex(int(time.time()))[2:]
        value = "%s%s%s" % (value, self.sep, timestamp)
        return super().sign(value)

    def unsign(self, value, max_age=None):
        result = super().unsign(value)
        value, timestamp_str = result.rsplit(self.sep, 1)
        timestamp = int(timestamp_str, base=16)
        if max_age is not None:
            age = time.time() - timestamp
            if age > max_age:
                raise SignatureExpired("Signature age %s > %s seconds" % (age, max_age))
        return value


def sign_bounce_id(s):
    return HexTimestampSigner(sep=".", algorithm="sha1").sign(s)


def unsign_bounce_id(s, max_age):
    return HexTimestampSigner(sep=".", algorithm="sha1").unsign(s, max_age=max_age)
