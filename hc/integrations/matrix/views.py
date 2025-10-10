from __future__ import annotations

from uuid import UUID

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.integrations.matrix.forms import AddMatrixForm


@require_setting("MATRIX_ACCESS_TOKEN")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = AddMatrixForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="matrix")
            channel.value = form.cleaned_data["room_id"]

            # If user supplied room alias instead of ID, use it as channel name
            alias = form.cleaned_data["alias"]
            if not alias.startswith("!"):
                channel.name = alias

            channel.save()

            channel.assign_all_checks()
            messages.success(request, "The Matrix integration has been added!")
            return redirect("hc-channels", project.code)
    else:
        form = AddMatrixForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
        "matrix_user_id": settings.MATRIX_USER_ID,
    }
    return render(request, "add_matrix.html", ctx)
