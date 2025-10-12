from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError


class Spike(HttpTransport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.SPIKE_ENABLED:
            raise TransportError("Spike notifications are not enabled.")

        url = self.channel.value
        headers = {"Content-Type": "application/json"}
        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "ping": self.last_ping(flip),
        }
        payload = {
            "check_id": str(flip.owner.unique_key),
            "title": self.tmpl("spike_title.html", **ctx),
            "message": self.tmpl("spike_description.html", **ctx),
            "status": flip.new_status,
        }

        self.post(url, json=payload, headers=headers)
