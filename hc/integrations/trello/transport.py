from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError


class Trello(HttpTransport):
    URL = "https://api.trello.com/1/cards"

    def is_noop(self, status: str) -> bool:
        return status != "down"

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.TRELLO_APP_KEY:
            raise TransportError("Trello notifications are not enabled.")

        ctx = {
            "check": flip.owner,
            "status": flip.new_status,
            "ping": self.last_ping(flip),
        }
        params = {
            "idList": self.channel.trello.list_id,
            "name": self.tmpl("trello_name.html", **ctx),
            "desc": self.tmpl("trello_desc.html", **ctx),
            "key": settings.TRELLO_APP_KEY,
            "token": self.channel.trello.token,
        }

        self.post(self.URL, params=params)
