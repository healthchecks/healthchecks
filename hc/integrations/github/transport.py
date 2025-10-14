from __future__ import annotations

from typing import NoReturn

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError, get_ping_body
from hc.integrations.github import client
from hc.lib import curl


class GitHub(HttpTransport):
    def is_noop(self, status: str) -> bool:
        return status != "down"

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        permanent = False
        if response.status_code == 410:
            # If GitHub returns HTTP 410 assume this will never work again
            permanent = True

        raise TransportError(message, permanent=permanent)

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.GITHUB_PRIVATE_KEY:
            raise TransportError("GitHub notifications are not enabled.")

        ping = self.last_ping(flip)
        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "ping": ping,
        }

        body = get_ping_body(ping, maxlen=1000)
        if body and "```" not in body:
            ctx["body"] = body

        url = f"https://api.github.com/repos/{self.channel.github.repo}/issues"
        payload = {
            "title": self.tmpl("github_title.html", **ctx),
            "body": self.tmpl("github_body.html", **ctx),
            "labels": self.channel.github.labels,
        }

        inst_id = self.channel.github.installation_id
        token = client.get_installation_access_token(inst_id)
        if token is None:
            raise TransportError(f"GitHub denied access to {self.channel.github.repo}")

        headers = {"Authorization": f"Bearer {token}"}
        self.post(url, json=payload, headers=headers)
