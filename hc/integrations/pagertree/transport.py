from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError


class PagerTree(HttpTransport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.PAGERTREE_ENABLED:
            raise TransportError("PagerTree notifications are not enabled.")

        url = self.channel.value
        headers = {"Content-Type": "application/json"}
        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "ping": self.last_ping(flip),
        }
        payload = {
            "incident_key": str(flip.owner.unique_key),
            "event_type": "trigger" if flip.new_status == "down" else "resolve",
            "title": self.tmpl("pagertree_title.html", **ctx),
            "description": self.tmpl("pagertree_description.html", **ctx),
            "client": settings.SITE_NAME,
            "client_url": settings.SITE_ROOT,
            "tags": " ".join(flip.owner.tags_list()),
        }

        self.post(url, json=payload, headers=headers)
