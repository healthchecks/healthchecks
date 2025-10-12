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


class Sms(HttpTransport):
    URL = "https://api.twilio.com/2010-04-01/Accounts/%s/Messages.json"

    class ErrorModel(BaseModel):
        code: int

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        if response.status_code == 400:
            try:
                doc = Sms.ErrorModel.model_validate_json(response.content, strict=True)
                if doc.code == 21211:
                    raise TransportError("Invalid phone number", permanent=True)
            except ValidationError:
                pass

            logger.debug("Twilio Messages HTTP 400 with body: %s", response.content)

        raise TransportError(f"Received status code {response.status_code}")

    def is_noop(self, status: str) -> bool:
        if status == "down":
            return not self.channel.phone.notify_down
        else:
            return not self.channel.phone.notify_up

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.TWILIO_ACCOUNT or not settings.TWILIO_AUTH:
            raise TransportError("SMS notifications are not enabled")

        profile = Profile.objects.for_user(self.channel.project.owner)
        if not profile.authorize_sms():
            profile.send_sms_limit_notice("SMS")
            raise TransportError("Monthly SMS limit exceeded")

        url = self.URL % settings.TWILIO_ACCOUNT
        auth = (settings.TWILIO_ACCOUNT, settings.TWILIO_AUTH)
        text = self.tmpl(
            "sms_message.html",
            flip=flip,
            check=flip.owner,
            status=flip.new_status,
            site_name=settings.SITE_NAME,
        )

        data = {
            "To": self.channel.phone.value,
            "Body": text,
            "StatusCallback": notification.status_url(),
            "RiskCheck": "disable",
        }

        if settings.TWILIO_MESSAGING_SERVICE_SID:
            data["MessagingServiceSid"] = settings.TWILIO_MESSAGING_SERVICE_SID
        else:
            assert settings.TWILIO_FROM
            data["From"] = settings.TWILIO_FROM

        self.post(url, data=data, auth=auth)
