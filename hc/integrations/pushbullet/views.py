from __future__ import annotations

import logging
from secrets import token_urlsafe
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.lib import curl
from hc.lib.urls import absolute_reverse
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


@require_setting("PUSHBULLET_CLIENT_ID")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = "https://www.pushbullet.com/authorize?" + urlencode(
        {
            "client_id": settings.PUSHBULLET_CLIENT_ID,
            "redirect_uri": absolute_reverse(add_complete),
            "response_type": "code",
            "state": state,
        }
    )

    ctx = {
        "page": "channels",
        "project": project,
        "authorize_url": authorize_url,
    }

    request.session["add_pushbullet"] = (state, str(project.code))
    return render(request, "add_pushbullet.html", ctx)


class PushbulletOAuthResponse(BaseModel):
    access_token: str


@require_setting("PUSHBULLET_CLIENT_ID")
@login_required
def add_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
    if "add_pushbullet" not in request.session:
        return HttpResponseForbidden()

    state, code_str = request.session.pop("add_pushbullet")
    code = UUID(code_str)
    project = _get_rw_project_for_user(request, code)

    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Pushbullet setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    data = {
        "client_id": settings.PUSHBULLET_CLIENT_ID,
        "client_secret": settings.PUSHBULLET_CLIENT_SECRET,
        "code": request.GET.get("code"),
        "grant_type": "authorization_code",
    }
    result = curl.post("https://api.pushbullet.com/oauth2/token", data)
    try:
        doc = PushbulletOAuthResponse.model_validate_json(result.content, strict=True)
    except ValidationError:
        logger.warning("Unexpected Pushbullet OAuth response: %s", result.content)
        messages.warning(
            request,
            "Received an unexpected response from Pushbullet. Integration not added.",
        )
        return redirect("hc-channels", project.code)

    channel = Channel(kind="pushbullet", project=project)
    channel.value = doc.access_token
    channel.save()
    channel.assign_all_checks()
    messages.success(request, "The Pushbullet integration has been added!")
    return redirect("hc-channels", project.code)
