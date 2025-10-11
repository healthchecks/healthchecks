from __future__ import annotations

from typing import NoReturn

from hc.api.models import Flip, Notification
from hc.api.transports import TransportError
from hc.integrations.slack.transport import Slackalike
from hc.lib import curl


class Discord(Slackalike):
    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        # Consider 404 a permanent failure
        permanent = response.status_code == 404
        raise TransportError(message, permanent=permanent)

    def notify(self, flip: Flip, notification: Notification) -> None:
        url = self.channel.discord_webhook_url + "/slack"

        prepared_payload = self.payload(flip)
        self.post(url, json=prepared_payload)

    def fix_asterisks(self, s: str) -> str:
        # In Discord notifications asterisks should be escaped with a backslash
        return s.replace("*", r"\*")
