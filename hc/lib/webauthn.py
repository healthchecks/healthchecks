import json
from secrets import token_bytes

from fido2.client import ClientData
from fido2.ctap2 import AttestationObject, AttestedCredentialData, AuthenticatorData
from fido2.server import Fido2Server
from fido2.utils import websafe_encode, websafe_decode


def bytes_to_b64(obj):
    if isinstance(obj, dict):
        return {k: bytes_to_b64(v) for k, v in obj.items()}

    if isinstance(obj, list):
        return [bytes_to_b64(v) for v in obj]

    if isinstance(obj, bytes):
        return websafe_encode(obj)

    return obj


json_decode_map = {
    "clientDataJSON": ClientData,
    "attestationObject": AttestationObject,
    "rawId": bytes,
    "authenticatorData": AuthenticatorData,
    "signature": bytes,
}


def json_decode_hook(d):
    for key, cls in json_decode_map.items():
        if key in d:
            as_bytes = websafe_decode(d[key])
            d[key] = cls(as_bytes)

    return d


class CreateHelper(object):
    def __init__(self, rp_id, credentials):
        self.server = Fido2Server({"id": rp_id, "name": "healthchecks"})
        self.credentials = [AttestedCredentialData(blob) for blob in credentials]

    def prepare(self, email):
        # User handle is used in a username-less authentication, to map a credential
        # received from browser with an user account in the database.
        # Since we only use security keys as a second factor,
        # the user handle is not of much use to us.
        #
        # The user handle:
        #  - must not be blank,
        #  - must not be a constant value,
        #  - must not contain personally identifiable information.
        # So we use random bytes, and don't store them on our end:
        user = {
            "id": token_bytes(16),
            "name": email,
            "displayName": email,
        }
        options, state = self.server.register_begin(user, self.credentials)
        return bytes_to_b64(options), state

    def verify(self, state, response_json):
        try:
            doc = json.loads(response_json, object_hook=json_decode_hook)
            auth_data = self.server.register_complete(
                state,
                doc["response"]["clientDataJSON"],
                doc["response"]["attestationObject"],
            )
            return auth_data.credential_data
        except ValueError:
            return None


class GetHelper(object):
    def __init__(self, rp_id, credentials):
        self.server = Fido2Server({"id": rp_id, "name": "healthchecks"})
        self.credentials = [AttestedCredentialData(blob) for blob in credentials]

    def prepare(self):
        options, state = self.server.authenticate_begin(self.credentials)
        return bytes_to_b64(options), state

    def verify(self, state, response_json):
        try:
            doc = json.loads(response_json, object_hook=json_decode_hook)
            self.server.authenticate_complete(
                state,
                self.credentials,
                doc["rawId"],
                doc["response"]["clientDataJSON"],
                doc["response"]["authenticatorData"],
                doc["response"]["signature"],
            )
            return True
        except ValueError:
            return False
