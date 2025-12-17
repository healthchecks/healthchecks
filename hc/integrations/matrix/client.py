from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from hc.lib import curl
from pydantic import BaseModel, Field, ValidationError

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
    url += "/_matrix/client/v3/join/" + quote(alias)
    headers = {"Authorization": f"Bearer {settings.MATRIX_ACCESS_TOKEN}"}
    r = curl.post(url, headers=headers)
    if r.status_code in JOIN_ERRORS:
        raise JoinError(JOIN_ERRORS[r.status_code])

    try:
        doc = MatrixJoinResponse.model_validate_json(r.content, strict=True)
    except ValidationError:
        raise JoinError("Matrix server returned unexpected response")

    return doc.room_id
