from __future__ import annotations

import json
from typing import Literal

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.api.transports import TransportError
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.integrations.telegram import forms
from hc.integrations.telegram.transport import Telegram
from pydantic import BaseModel, ValidationError


class TelegramChat(BaseModel):
    id: int
    type: Literal["group", "private", "supergroup", "channel"]
    title: str | None = None
    username: str | None = None


class TelegramMessage(BaseModel):
    chat: TelegramChat
    text: str
    message_thread_id: int | None = None


class TelegramCallback(BaseModel):
    message: TelegramMessage

    @classmethod
    def load(self, data: bytes) -> TelegramCallback:
        doc = json.loads(data.decode())
        if "channel_post" in doc:
            # Telegram's "channel_post" key uses the same structure as "message".
            # To keep the validation and view logic simple, if the payload
            # contains "channel_post", copy it to "message", and proceed as usual.
            doc["message"] = doc["channel_post"]
        return TelegramCallback.model_validate(doc, strict=True)


@csrf_exempt
@require_POST
def telegram_bot(request: HttpRequest) -> HttpResponse:
    try:
        doc = TelegramCallback.load(request.body)
    except ValidationError:
        # We don't recognize the message format, but don't want Telegram
        # retrying this over and over again, so respond with 200 OK
        return HttpResponse()
    except ValueError:
        return HttpResponseBadRequest()

    if "/start" not in doc.message.text:
        return HttpResponse()

    chat = doc.message.chat
    recipient = {
        "id": chat.id,
        "type": chat.type,
        "name": chat.title or chat.username,
        "thread_id": doc.message.message_thread_id,
    }

    invite = render_to_string(
        "telegram_invite.html",
        {"qs": signing.dumps(recipient)},
    )

    try:
        Telegram.send(chat.id, doc.message.message_thread_id, invite)
    except TransportError:
        # Swallow the error and return HTTP 200 OK, otherwise Telegram will
        # hit the webhook again and again.
        pass

    return HttpResponse()


@require_setting("TELEGRAM_TOKEN")
def telegram_help(request: HttpRequest) -> HttpResponse:
    ctx = {
        "page": "channels",
        "bot_name": settings.TELEGRAM_BOT_NAME,
    }

    return render(request, "add_telegram.html", ctx)


@require_setting("TELEGRAM_TOKEN")
@login_required
def add(request: AuthenticatedHttpRequest) -> HttpResponse:
    recipient = None
    if qs := request.META["QUERY_STRING"]:
        try:
            recipient = signing.loads(qs, max_age=600)
            assert isinstance(recipient, dict)
        except signing.BadSignature:
            return render(request, "bad_link.html")

    if request.method == "POST":
        form = forms.AddTelegramForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        project = _get_rw_project_for_user(request, form.cleaned_data["project"])
        channel = Channel(project=project, kind="telegram")
        channel.value = json.dumps(recipient)
        channel.save()

        channel.assign_all_checks()
        messages.success(request, "The Telegram integration has been added!")
        return redirect("hc-channels", project.code)

    ctx = {
        "page": "channels",
        "projects": request.profile.projects(),
        "recipient": recipient,
        "bot_name": settings.TELEGRAM_BOT_NAME,
    }

    return render(request, "add_telegram.html", ctx)
