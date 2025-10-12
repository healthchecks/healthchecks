from __future__ import annotations

from urllib.parse import quote, urlencode

from django.conf import settings
from pydantic import BaseModel, Field, ValidationError

from hc.lib import curl

JOIN_ERRORS = {
    429: "Matrix server returned status 429 (Too Many Requests), please try later.",
    502: "Matrix server returned status 502 (Bad Gateway), please try later.",
}


class JoinError(Exception):
    def __init__(self, message: str) -> None:
        self.message = message


class MatrixJoinResponse(BaseModel):
    room_id: str = Field(min_length=1)


def join(alias: str) -> str:
    assert settings.MATRIX_HOMESERVER
    url = settings.MATRIX_HOMESERVER
    url += "/_matrix/client/r0/join/%s?" % quote(alias)
    url += urlencode({"access_token": settings.MATRIX_ACCESS_TOKEN})
    r = curl.post(url)
    if r.status_code in JOIN_ERRORS:
        raise JoinError(JOIN_ERRORS[r.status_code])

    try:
        doc = MatrixJoinResponse.model_validate_json(r.content, strict=True)
    except ValidationError:
        raise JoinError("Matrix server returned unexpected response")

    return doc.room_id
