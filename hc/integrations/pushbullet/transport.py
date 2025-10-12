from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport


class Pushbullet(HttpTransport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        url = "https://api.pushbullet.com/v2/pushes"
        headers = {
            "Access-Token": self.channel.value,
            "Content-Type": "application/json",
        }
        text = self.tmpl(
            "pushbullet_message.html",
            flip=flip,
            check=flip.owner,
            status=flip.new_status,
        )
        payload = {"type": "note", "title": settings.SITE_NAME, "body": text}
        self.post(url, json=payload, headers=headers)
