from __future__ import annotations

import json
from secrets import token_urlsafe
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.integrations.pd import forms
from hc.lib.urls import absolute_reverse


@require_setting("PD_ENABLED")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    # Simple Install Flow
    if settings.PD_APP_ID:
        state = token_urlsafe()
        redirect_url = absolute_reverse("hc-add-pd-complete", query={"state": state})
        install_url = "https://app.pagerduty.com/install/integration?" + urlencode(
            {"app_id": settings.PD_APP_ID, "redirect_url": redirect_url, "version": "2"}
        )

        ctx = {"page": "channels", "project": project, "install_url": install_url}
        request.session["pagerduty"] = (state, str(project.code))
        return render(request, "add_pd_simple.html", ctx)

    if request.method == "POST":
        form = forms.AddPdForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="pd")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddPdForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "add_pd.html", ctx)


@require_setting("PD_ENABLED")
@require_setting("PD_APP_ID")
@login_required
def add_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
    if "pagerduty" not in request.session:
        return HttpResponseBadRequest()

    state, code_str = request.session.pop("pagerduty")
    code = UUID(code_str)
    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    project = _get_rw_project_for_user(request, code)

    doc = json.loads(request.GET["config"])
    for item in doc["integration_keys"]:
        channel = Channel(kind="pd", project=project)
        channel.name = item["name"]
        channel.value = json.dumps(
            {"service_key": item["integration_key"], "account": doc["account"]["name"]}
        )
        channel.save()
        channel.assign_all_checks()

    messages.success(request, "The PagerDuty integration has been added!")
    return redirect("hc-channels", project.code)


@require_setting("PD_ENABLED")
@require_setting("PD_APP_ID")
def pd_help(request: HttpRequest) -> HttpResponse:
    ctx = {"page": "channels"}
    return render(request, "add_pd_simple.html", ctx)
