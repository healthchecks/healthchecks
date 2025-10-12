from __future__ import annotations

from urllib.parse import urlencode, urljoin

from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport


class Gotify(HttpTransport):
    def notify(self, flip: Flip, notification: Notification) -> None:
        base = self.channel.gotify.url
        if not base.endswith("/"):
            base += "/"

        url = urljoin(base, "message")
        url += "?" + urlencode({"token": self.channel.gotify.token})

        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "down_checks": self.down_checks(flip.owner),
        }
        payload = {
            "title": self.tmpl("gotify_title.html", **ctx),
            "message": self.tmpl("gotify_message.html", **ctx),
            "extras": {
                "client::display": {"contentType": "text/markdown"},
            },
        }

        self.post(url, json=payload)
