from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.views import _get_rw_project_for_user
from hc.integrations.ntfy.forms import NtfyForm


def ntfy_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = NtfyForm(request.POST)
        if form.is_valid():
            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = NtfyForm()
    else:
        form = NtfyForm(
            {
                "topic": channel.ntfy.topic,
                "url": channel.ntfy.url,
                "priority": channel.ntfy.priority,
                "priority_up": channel.ntfy.priority_up,
                "token": channel.ntfy.token,
            }
        )

    ctx = {"page": "channels", "project": channel.project, "form": form}
    return render(request, "ntfy_form.html", ctx)


@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="ntfy")
    return ntfy_form(request, channel)
