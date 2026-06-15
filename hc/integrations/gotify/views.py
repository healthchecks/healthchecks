from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.views import _get_rw_project_for_user
from hc.integrations.gotify.forms import GotifyForm


@login_required
def gotify_form(request: AuthenticatedHttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = GotifyForm(request.POST)
        if form.is_valid():
            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = GotifyForm()
    else:
        # When editing an existing integration, if priority is not set
        # then use normal priority as the default.
        def setdefault(prio: int | None) -> int:
            if prio is None:
                return 5
            return prio

        form = GotifyForm(
            {
                "token": channel.gotify.token,
                "url": channel.gotify.url,
                "priority": setdefault(channel.gotify.priority),
                "priority_up": setdefault(channel.gotify.priority_up),
            }
        )

    ctx = {"page": "channels", "project": channel.project, "form": form}
    return render(request, "gotify_form.html", ctx)


@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="gotify")
    return gotify_form(request, channel)
