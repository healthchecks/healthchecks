from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.views import _get_rw_project_for_user
from hc.integrations.gotify.forms import AddGotifyForm


@login_required
def add_gotify(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = AddGotifyForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="gotify")
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = AddGotifyForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "add_gotify.html", ctx)
