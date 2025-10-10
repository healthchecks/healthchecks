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

logger = logging.getLogger(__name__)


@require_setting("DISCORD_CLIENT_ID")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    state = token_urlsafe()
    auth_url = "https://discordapp.com/api/oauth2/authorize?" + urlencode(
        {
            "client_id": settings.DISCORD_CLIENT_ID,
            "scope": "webhook.incoming",
            "redirect_uri": absolute_reverse(add_complete),
            "response_type": "code",
            "state": state,
        }
    )

    ctx = {"page": "channels", "project": project, "authorize_url": auth_url}

    request.session["add_discord"] = (state, str(project.code))
    return render(request, "add_discord.html", ctx)


@require_setting("DISCORD_CLIENT_ID")
@login_required
def add_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
    if "add_discord" not in request.session:
        return HttpResponseForbidden()

    state, code_str = request.session.pop("add_discord")
    code = UUID(code_str)
    project = _get_rw_project_for_user(request, code)

    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Discord setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    data = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "client_secret": settings.DISCORD_CLIENT_SECRET,
        "code": request.GET.get("code"),
        "grant_type": "authorization_code",
        "redirect_uri": absolute_reverse(add_complete),
    }
    result = curl.post("https://discordapp.com/api/oauth2/token", data)

    doc = result.json()
    if isinstance(doc, dict) and doc.get("code") == 30007:
        e = "maximum number of webhooks reached"
        messages.warning(request, f"Response from Discord: {e}. Integration not added.")
        return redirect("hc-channels", project.code)

    if not isinstance(doc, dict) or "access_token" not in doc:
        messages.warning(
            request,
            "Received an unexpected response from Discord. Integration not added.",
        )
        logger.warning("Unexpected Discord OAuth response: %s", result.content)
        return redirect("hc-channels", project.code)

    channel = Channel(kind="discord", project=project)
    channel.value = result.text
    channel.save()
    channel.assign_all_checks()
    messages.success(request, "The Discord integration has been added!")
    return redirect("hc-channels", project.code)
