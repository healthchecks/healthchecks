from __future__ import annotations

from typing import NoReturn

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError
from hc.lib import curl
from pydantic import BaseModel, ValidationError


class Zulip(HttpTransport):
    class ErrorModel(BaseModel):
        msg: str

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        try:
            f = Zulip.ErrorModel.model_validate_json(response.content)
            message += f' with a message: "{f.msg}"'
        except ValidationError:
            pass

        raise TransportError(message)

    def notify(self, flip: Flip, notification: Notification) -> None:
        if not settings.ZULIP_ENABLED:
            raise TransportError("Zulip notifications are not enabled.")

        topic = self.channel.zulip.topic
        if not topic:
            topic = self.tmpl(
                "zulip_topic.html", check=flip.owner, status=flip.new_status
            )

        url = self.channel.zulip.site + "/api/v1/messages"
        auth = (self.channel.zulip.bot_email, self.channel.zulip.api_key)
        content = self.tmpl(
            "zulip_content.html",
            flip=flip,
            check=flip.owner,
            status=flip.new_status,
        )
        data = {
            "type": self.channel.zulip.mtype,
            "to": self.channel.zulip.formatted_to(),
            "topic": topic,
            "content": content,
        }

        self.post(url, data=data, auth=auth)
