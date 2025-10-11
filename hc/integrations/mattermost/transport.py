from __future__ import annotations

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import TransportError
from hc.integrations.slack.transport import Slackalike


class Mattermost(Slackalike):
    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.MATTERMOST_ENABLED:
            raise TransportError("Mattermost notifications are not enabled.")

        prepared_payload = self.payload(flip)
        self.post(self.channel.slack_webhook_url, json=prepared_payload)
