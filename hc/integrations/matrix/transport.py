from __future__ import annotations

from urllib.parse import quote, urlencode

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, get_ping_body


class Matrix(HttpTransport):
    def get_url(self) -> str:
        room_id = quote(self.channel.value)

        assert isinstance(settings.MATRIX_HOMESERVER, str)
        url = settings.MATRIX_HOMESERVER
        url += f"/_matrix/client/r0/rooms/{room_id}/send/m.room.message?"
        url += urlencode({"access_token": settings.MATRIX_ACCESS_TOKEN})
        return url

    def notify(self, flip: Flip, notification: Notification) -> None:
        ping = self.last_ping(flip)
        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "ping": ping,
            "body": get_ping_body(ping, maxlen=1000),
            "down_checks": self.down_checks(flip.owner),
        }
        plain = self.tmpl("matrix_description.html", **ctx)
        formatted = self.tmpl("matrix_description_formatted.html", **ctx)
        payload = {
            "msgtype": "m.text",
            "body": plain,
            "format": "org.matrix.custom.html",
            "formatted_body": formatted,
        }

        self.post(self.get_url(), json=payload)
