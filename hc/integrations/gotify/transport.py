from __future__ import annotations

from urllib.parse import urlencode, urljoin

from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport
from hc.lib.typealias import JSONDict


class Gotify(HttpTransport):
    def priority_for_status(self, status: str) -> int | None:
        cfg = self.channel.gotify
        return cfg.priority_up if status == "up" else cfg.priority

    def is_noop(self, status: str) -> bool:
        return self.priority_for_status(status) == 0

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
        payload: JSONDict = {
            "title": self.tmpl("gotify_title.html", **ctx),
            "message": self.tmpl("gotify_message.html", **ctx),
            "extras": {
                "client::display": {"contentType": "text/markdown"},
            },
        }

        priority = self.priority_for_status(flip.new_status)
        if priority is not None:
            payload["priority"] = priority

        self.post(url, json=payload)
