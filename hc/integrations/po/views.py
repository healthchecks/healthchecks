from __future__ import annotations

from datetime import timedelta as td
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
from hc.integrations.po import forms
from hc.lib.urls import absolute_reverse


@require_setting("PUSHOVER_API_TOKEN")
def pushover_help(request: HttpRequest) -> HttpResponse:
    ctx = {"page": "channels"}
    return render(request, "add_pushover_help.html", ctx)


@require_setting("PUSHOVER_API_TOKEN")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        state = token_urlsafe().lower()

        failure_url = absolute_reverse("hc-channels", args=[project.code])
        success_url = absolute_reverse(
            "hc-add-pushover",
            args=[project.code],
            query={
                "state": state,
                "prio": request.POST.get("po_priority", "0"),
                "prio_up": request.POST.get("po_priority_up", "0"),
            },
        )
        assert settings.PUSHOVER_SUBSCRIPTION_URL
        subscription_url = (
            settings.PUSHOVER_SUBSCRIPTION_URL
            + "?"
            + urlencode({"success": success_url, "failure": failure_url})
        )

        request.session["pushover"] = state
        return redirect(subscription_url)

    # Handle successful subscriptions
    if "pushover_user_key" in request.GET:
        if "pushover" not in request.session:
            return HttpResponseForbidden()

        state = request.session.pop("pushover")
        if request.GET.get("state") != state:
            return HttpResponseForbidden()

        if request.GET.get("pushover_unsubscribed") == "1":
            # Unsubscription: delete all Pushover channels for this project
            Channel.objects.filter(project=project, kind="po").delete()
            return redirect("hc-channels", project.code)

        form = forms.AddPushoverForm(request.GET)
        if not form.is_valid():
            return HttpResponseBadRequest()

        channel = Channel(project=project, kind="po")
        channel.value = form.get_value()
        channel.save()
        channel.assign_all_checks()

        messages.success(request, "The Pushover integration has been added!")
        return redirect("hc-channels", project.code)

    # Show Integration Settings form
    ctx = {
        "page": "channels",
        "project": project,
        "po_retry_delay": td(seconds=settings.PUSHOVER_EMERGENCY_RETRY_DELAY),
        "po_expiration": td(seconds=settings.PUSHOVER_EMERGENCY_EXPIRATION),
    }
    return render(request, "add_pushover.html", ctx)
