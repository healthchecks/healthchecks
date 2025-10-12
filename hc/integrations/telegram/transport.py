from __future__ import annotations

from typing import NoReturn

from django.conf import settings
from hc.api.models import Flip, Notification
from hc.api.transports import HttpTransport, TransportError, get_ping_body
from hc.lib import curl
from pydantic import BaseModel, ValidationError


class MigrationRequiredError(TransportError):
    def __init__(self, message: str, new_chat_id: int):
        super().__init__(message, permanent=True)
        self.new_chat_id = new_chat_id


class Telegram(HttpTransport):
    SM = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"

    class MigrationParameters(BaseModel):
        migrate_to_chat_id: int

    class ErrorModel(BaseModel):
        description: str
        parameters: Telegram.MigrationParameters | None = None

    @classmethod
    def raise_for_response(cls, response: curl.Response) -> NoReturn:
        message = f"Received status code {response.status_code}"
        try:
            m = Telegram.ErrorModel.model_validate_json(response.content)
        except ValidationError:
            raise TransportError(message)

        if m.parameters:
            # If the error payload contains the migrate_to_chat_id field,
            # raise MigrationRequiredError, with the new chat_id included
            chat_id = m.parameters.migrate_to_chat_id
            raise MigrationRequiredError(m.description, chat_id)

        permanent = False
        message += f' with a message: "{m.description}"'
        if m.description == "Forbidden: the group chat was deleted":
            permanent = True
        elif m.description == "Forbidden: bot was blocked by the user":
            permanent = True
        elif m.description == "Forbidden: user is deactivated":
            permanent = True

        raise TransportError(message, permanent=permanent)

    @classmethod
    def send(cls, chat_id: int, thread_id: int | None, text: str) -> None:
        # Telegram.send is a separate method because it is also used in
        # hc.front.views.telegram_bot to send invite links.
        payload = {
            "chat_id": chat_id,
            "message_thread_id": thread_id,
            "text": text,
            "parse_mode": "html",
        }
        cls.post(cls.SM, json=payload)

    def notify(self, flip: Flip, notification: Notification) -> None:
        from hc.api.models import TokenBucket

        if not TokenBucket.authorize_telegram(self.channel.telegram.id):
            raise TransportError("Rate limit exceeded")

        ping = self.last_ping(flip)
        ctx = {
            "flip": flip,
            "check": flip.owner,
            "status": flip.new_status,
            "down_checks": self.down_checks(flip.owner),
            "ping": ping,
            # Telegram's message limit is 4096 chars, but clip body at 1000 for
            # consistency
            "body": get_ping_body(ping, maxlen=1000),
        }
        text = self.tmpl("telegram_message.html", **ctx)

        try:
            self.send(self.channel.telegram.id, self.channel.telegram.thread_id, text)
        except MigrationRequiredError as e:
            # Save the new chat_id, then try sending again:
            self.channel.update_telegram_id(e.new_chat_id)
            self.send(self.channel.telegram.id, self.channel.telegram.thread_id, text)
