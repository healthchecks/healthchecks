from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render

from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.integrations.shell.forms import ShellForm


@require_setting("SHELL_ENABLED")
@login_required
def shell_form(request: AuthenticatedHttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = ShellForm(request.POST)
        if form.is_valid():
            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = ShellForm()
    else:
        form = ShellForm(
            {"cmd_up": channel.shell.cmd_up, "cmd_down": channel.shell.cmd_down}
        )

    ctx = {
        "page": "channels",
        "project": channel.project,
        "form": form,
        "is_new": adding,
    }
    return render(request, "shell_form.html", ctx)


@require_setting("SHELL_ENABLED")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="shell")
    return shell_form(request, channel)
