from __future__ import annotations

import logging
from typing import NoReturn

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.lib import curl
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class Pushover(HttpTransport):
    URL = "https://api.pushover.net/1/messages.json"
    CANCEL_TMPL = "https://api.pushover.net/1/receipts/cancel_by_tag/%s.json"

    class ErrorModel(BaseModel):
        user: str = ""

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        permanent = False
        if response.status_code == 400:
            try:
                doc = Pushover.ErrorModel.model_validate_json(response.content)
                if doc.user == "invalid":
                    message += " (invalid user)"
                    permanent = True
            except ValidationError:
                logger.debug("Pushover HTTP 400 with body: %s", response.content)

        raise TransportError(message, permanent=permanent)

    def is_noop(self, status: str) -> bool:
        pieces = self.channel.value.split("|")
        _, prio = pieces[0], pieces[1]

        # The third element, if present, is the priority for "up" events
        if status == "up" and len(pieces) == 3:
            prio = pieces[2]

        return int(prio) == -3

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.PUSHOVER_API_TOKEN:
            raise TransportError("Pushover notifications are not enabled.")

        pieces = self.channel.value.split("|")
        user_key, down_prio = pieces[0], pieces[1]

        # The third element, if present, is the priority for "up" events
        up_prio = down_prio
        if len(pieces) == 3:
            up_prio = pieces[2]

        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_pushover(user_key):
            raise TransportError("Rate limit exceeded")

        check = flip.owner
        # If down events have the emergency priority,
        # send a cancel call first
        if flip.new_status == "up" and down_prio == "2":
            url = self.CANCEL_TMPL % check.unique_key
            cancel_payload = {"token": settings.PUSHOVER_API_TOKEN}
            self.post(url, data=cancel_payload)

        ctx = {
            "flip": flip,
            "check": check,
            "status": flip.new_status,
            "ping": self.last_ping(flip),
            "down_checks": self.down_checks(check),
        }
        text = self.tmpl("pushover_message.html", **ctx)
        title = self.tmpl("pushover_title.html", **ctx)
        prio = up_prio if flip.new_status == "up" else down_prio

        payload = {
            "token": settings.PUSHOVER_API_TOKEN,
            "user": user_key,
            "message": text,
            "title": title,
            "html": 1,
            "priority": int(prio),
            "tags": check.unique_key,
            "url": check.cloaked_url(),
            "url_title": f"View on {settings.SITE_NAME}",
        }

        # Emergency notification
        if prio == "2":
            payload["retry"] = settings.PUSHOVER_EMERGENCY_RETRY_DELAY
            payload["expire"] = settings.PUSHOVER_EMERGENCY_EXPIRATION

        self.post(self.URL, data=payload)
