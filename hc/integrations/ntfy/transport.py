from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError


class Ntfy(HttpTransport):
    def priority(self, status: str) -> int:
        if status == "up":
            return self.channel.ntfy.priority_up
        return self.channel.ntfy.priority

    def is_noop(self, status: str) -> bool:
        return self.priority(status) == 0

    def notify(self, flip: Flip, notification: Notification) -> None:
        ntfy = self.channel.ntfy
        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_ntfy(ntfy.url, ntfy.topic):
            raise TransportError("Rate limit exceeded")

        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "ping": self.last_ping(flip),
            "down_checks": self.down_checks(flip.owner),
        }
        payload = {
            "topic": self.channel.ntfy.topic,
            "priority": self.priority(flip.new_status),
            "title": self.tmpl("ntfy_title.html", **ctx),
            "message": self.tmpl("ntfy_message.html", **ctx),
            "tags": ["red_circle" if flip.new_status == "down" else "green_circle"],
            "actions": [
                {
                    "action": "view",
                    "label": f"View on {settings.SITE_NAME}",
                    "url": flip.owner.cloaked_url(),
                }
            ],
        }

        url = self.channel.ntfy.url
        headers = {}
        if self.channel.ntfy.token:
            headers = {"Authorization": f"Bearer {self.channel.ntfy.token}"}
        elif url == "https://ntfy.sh" and settings.NTFY_SH_TOKEN:
            headers = {"Authorization": f"Bearer {settings.NTFY_SH_TOKEN}"}

        self.post(url, headers=headers, json=payload)
