from __future__ import annotations

import json
from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.integrations.webhook import forms


@require_setting("WEBHOOKS_ENABLED")
def webhook_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.WebhookForm(request.POST)
        if form.is_valid():
            channel.name = form.cleaned_data["name"]
            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()

            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.WebhookForm()
    else:

        def flatten(d: dict[str, str]) -> str:
            return "\n".join("%s: %s" % pair for pair in d.items())

        doc = json.loads(channel.value)
        doc["headers_down"] = flatten(doc["headers_down"])
        doc["headers_up"] = flatten(doc["headers_up"])
        doc["name"] = channel.name
        form = forms.WebhookForm(doc)

    ctx = {
        "page": "channels",
        "project": channel.project,
        "form": form,
        "is_new": adding,
    }
    return render(request, "webhook_form.html", ctx)


@require_setting("WEBHOOKS_ENABLED")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="webhook")
    return webhook_form(request, channel)
