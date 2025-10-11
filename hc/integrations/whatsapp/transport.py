from __future__ import annotations

import json
import logging
from typing import NoReturn

from django.conf import settings
from hc.accounts.models import Profile
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.lib import curl
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class WhatsApp(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    class ErrorModel(BaseModel):
        code: int

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        if response.status_code == 400:
            try:
                doc = WhatsApp.ErrorModel.model_validate_json(
                    response.content, strict=True
                )
                if doc.code == 21211:
                    raise TransportError("Invalid phone number", permanent=True)
            except ValidationError:
                pass

            logger.debug("WhatsApp HTTP 400 with body: %s", response.content)

        raise TransportError(f"Received status code {response.status_code}")

    def is_noop(self, status: str) -> bool:
        if status == "down":
            return not self.channel.phone.notify_down
        else:
            return not self.channel.phone.notify_up

    def notify(self, flip: Flip, notification: Notification) -> None:
        for key in (
            "TWILIO_USE_WHATSAPP",
            "TWILIO_ACCOUNT",
            "TWILIO_AUTH",
            "TWILIO_FROM",
            "TWILIO_MESSAGING_SERVICE_SID",
            "WHATSAPP_DOWN_CONTENT_SID",
            "WHATSAPP_UP_CONTENT_SID",
        ):
            if not getattr(settings, key):
                raise TransportError("WhatsApp notifications are not enabled")

        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            profile.send_sms_limit_notice("WhatsApp")
            raise TransportError("Monthly message limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        assert settings.TWILIO_ACCOUNT and settings.TWILIO_AUTH
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        if flip.new_status == "down":
            content_sid = settings.WHATSAPP_DOWN_CONTENT_SID
        else:
            content_sid = settings.WHATSAPP_UP_CONTENT_SID

        data = {
            "To": f"whatsapp:{self.channel.phone.value}",
            "From": f"whatsapp:{settings.TWILIO_FROM}",
            "MessagingServiceSid": settings.TWILIO_MESSAGING_SERVICE_SID,
            "ContentSid": content_sid,
            "ContentVariables": json.dumps({1: flip.owner.name_then_code()}),
            "StatusCallback": notification.status_url(),
        }

        self.post(url, data=data, auth=auth)
