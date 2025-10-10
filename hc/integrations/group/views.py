from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.views import _get_rw_project_for_user
from hc.integrations.group.forms import GroupForm


def group_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = GroupForm(request.POST, project=channel.project)
        if form.is_valid():
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = GroupForm(project=channel.project)
    else:
        # Filter out unavailable channels
        channels = list(channel.group_channels.values_list("code", flat=True))
        form = GroupForm(
            {"channels": channels, "label": channel.name}, project=channel.project
        )

    ctx = {"page": "channels", "project": channel.project, "form": form}
    return render(request, "group_form.html", ctx)


@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="group")
    return group_form(request, channel)
