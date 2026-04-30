from __future__ import annotations

import logging
from typing import NoReturn
from xml.sax.saxutils import escape

from django.conf import settings
from pydantic import BaseModel, ValidationError

from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.lib import curl

logger = logging.getLogger(__name__)


class Call(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Calls.json"

    class ErrorModel(BaseModel):
        code: int

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        if response.status_code == 400:
            try:
                doc = Call.ErrorModel.model_validate_json(response.content, strict=True)
                if doc.code == 21211:
                    raise TransportError("Invalid phone number", permanent=True)
            except ValidationError:
                pass

            logger.debug("Twilio Calls HTTP 400 with body: %s", response.content)
        raise TransportError(f"Received status code {response.status_code}")

    def is_noop(self, status: str) -> bool:
        return status != "down"

    def notify(self, flip: Flip, notification: Notification) -> None:
        if (
            not settings.TWILIO_ACCOUNT
            or not settings.TWILIO_AUTH
            or not settings.TWILIO_FROM
        ):
            raise TransportError("Call notifications are not enabled")

        ctx = {"check": flip.owner, "site_name": settings.SITE_NAME}
        message = self.tmpl("call_message.html", **ctx)

        profile = self.channel.project.owner_profile
        if not profile.authorize_call():
            self.channel.send_call_limit_notice(message)
            raise TransportError("Monthly phone call limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        escaped_message = escape(message)
        data = {
            "From": settings.TWILIO_FROM,
            "To": self.channel.phone.value,
            "Twiml": f"<Response><Say>{escaped_message}</Say></Response>",
            "StatusCallback": notification.status_url(),
        }

        self.post(url, data=data, auth=auth)
