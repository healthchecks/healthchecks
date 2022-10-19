from __future__ import annotations

import json
from secrets import token_bytes

import fido2.features
from fido2.server import Fido2Server
from fido2.webauthn import (
    AttestedCredentialData,
    PublicKeyCredentialRpEntity,
    PublicKeyCredentialUserEntity,
)

fido2.features.webauthn_json_mapping.enabled = True


class CreateHelper(object):
    def __init__(self, rp_id: str, credentials: list[bytes]):
        rp = PublicKeyCredentialRpEntity(id=rp_id, name="healthchecks")
        self.server = Fido2Server(rp)
        self.credentials = [AttestedCredentialData(blob) for blob in credentials]

    def prepare(self, email: str) -> tuple[dict, dict]:
        # User handle (id) is used in a username-less authentication, to map a
        # credential received from browser with an user account in the database.
        # Since we only use security keys as a second factor,
        # the user handle is not of much use to us.
        #
        # The user handle:
        #  - must not be blank,
        #  - must not be a constant value,
        #  - must not contain personally identifiable information.
        # So we use random bytes, and don't store them on our end:
        user = PublicKeyCredentialUserEntity(
            id=token_bytes(16),
            name=email,
            display_name=email,
        )
        options, state = self.server.register_begin(user, self.credentials)
        return dict(options), state

    def verify(self, state: dict, response_json: str) -> bytes | None:
        try:
            doc = json.loads(response_json)
            auth_data = self.server.register_complete(state, doc)
            return auth_data.credential_data
        except ValueError:
            return None


class GetHelper(object):
    def __init__(self, rp_id: str, credentials: list[bytes]):
        rp = PublicKeyCredentialRpEntity(id=rp_id, name="healthchecks")
        self.server = Fido2Server(rp)
        self.credentials = [AttestedCredentialData(blob) for blob in credentials]

    def prepare(self) -> tuple[dict, dict]:
        options, state = self.server.authenticate_begin(self.credentials)
        return dict(options), state

    def verify(self, state: dict, response_json: str) -> bool:
        try:
            doc = json.loads(response_json)
            self.server.authenticate_complete(state, self.credentials, doc)
            return True
        except ValueError:
            return False
