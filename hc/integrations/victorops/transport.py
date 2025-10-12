from __future__ import annotations

from typing import NoReturn

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.lib import curl


class VictorOps(HttpTransport):
    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        # If the endpoint returns 404, this endpoint is unlikely to ever work again
        permanent = response.status_code == 404
        raise TransportError(message, permanent=permanent)

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.VICTOROPS_ENABLED:
            raise TransportError("Splunk On-Call notifications are not enabled.")

        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
        }
        mtype = "CRITICAL" if flip.new_status == "down" else "RECOVERY"
        payload = {
            "entity_id": str(flip.owner.unique_key),
            "message_type": mtype,
            "entity_display_name": flip.owner.name_then_code(),
            "state_message": self.tmpl("victorops_description.html", **ctx),
            "monitoring_tool": settings.SITE_NAME,
        }

        self.post(self.channel.value, json=payload)
