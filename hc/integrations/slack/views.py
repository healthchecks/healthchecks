from __future__ import annotations

import logging
from secrets import token_urlsafe
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front import forms
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.lib import curl

logger = logging.getLogger(__name__)


@require_setting("SLACK_ENABLED")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="slack")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {
        "page": "channels",
        "form": form,
    }

    return render(request, "add_slack.html", ctx)


@require_setting("SLACK_ENABLED")
@require_setting("SLACK_CLIENT_ID")
def slack_help(request: HttpRequest) -> HttpResponse:
    ctx = {"page": "channels"}
    return render(request, "add_slack_btn.html", ctx)


@require_setting("SLACK_ENABLED")
@require_setting("SLACK_CLIENT_ID")
@login_required
def add_btn(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = "https://slack.com/oauth/v2/authorize?" + urlencode(
        {
            "scope": "incoming-webhook",
            "client_id": settings.SLACK_CLIENT_ID,
            "state": state,
        }
    )

    ctx = {
        "project": project,
        "page": "channels",
        "authorize_url": authorize_url,
    }

    request.session["add_slack"] = (state, str(project.code))
    return render(request, "add_slack_btn.html", ctx)


@require_setting("SLACK_ENABLED")
@require_setting("SLACK_CLIENT_ID")
@login_required
def add_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
    if "add_slack" not in request.session:
        return HttpResponseForbidden()

    state, code_str = request.session.pop("add_slack")
    code = UUID(code_str)
    project = _get_rw_project_for_user(request, code)
    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Slack setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    data = {
        "client_id": settings.SLACK_CLIENT_ID,
        "client_secret": settings.SLACK_CLIENT_SECRET,
        "code": request.GET.get("code"),
    }
    result = curl.post("https://slack.com/api/oauth.v2.access", data)

    doc = result.json()
    if not isinstance(doc, dict) or not doc.get("ok"):
        messages.warning(
            request,
            "Received an unexpected response from Slack. Integration not added.",
        )
        logger.warning("Unexpected Slack OAuth response: %s", result.content)
        return redirect("hc-channels", project.code)

    channel = Channel(kind="slack", project=project)
    channel.value = result.text
    if channel.slack_channel:
        channel.name = channel.slack_channel
    channel.save()
    channel.assign_all_checks()

    messages.success(request, "Success, integration added!")
    return redirect("hc-channels", project.code)
