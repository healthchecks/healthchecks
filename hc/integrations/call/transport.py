from __future__ import annotations

import logging
from typing import NoReturn

from django.conf import settings
from hc.accounts.models import Profile
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.lib import curl
from pydantic import BaseModel, ValidationError

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

        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_call():
            profile.send_call_limit_notice()
            raise TransportError("Monthly phone call limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        ctx = {"check": flip.owner, "site_name": settings.SITE_NAME}
        data = {
            "From": settings.TWILIO_FROM,
            "To": self.channel.phone.value,
            "Twiml": self.tmpl("call_message.html", **ctx),
            "StatusCallback": notification.status_url(),
        }

        self.post(url, data=data, auth=auth)
