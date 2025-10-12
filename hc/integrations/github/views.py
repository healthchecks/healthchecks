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
from django.views.decorators.http import require_POST
from hc.api.models import Channel
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.integrations.github import client, forms


@require_setting("GITHUB_CLIENT_ID")
@login_required
def add(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = "https://github.com/login/oauth/authorize?"
    authorize_url += urlencode({"client_id": settings.GITHUB_CLIENT_ID, "state": state})
    ctx = {
        "project": project,
        "authorize_url": authorize_url,
    }

    request.session["add_github_state"] = state
    request.session["add_github_project"] = str(project.code)
    return render(request, "add_github.html", ctx)


@require_setting("GITHUB_CLIENT_ID")
@login_required
def select(request: HttpRequest) -> HttpResponse:
    if "add_github_project" not in request.session:
        return HttpResponseForbidden()

    project_code = UUID(request.session["add_github_project"])
    project = _get_rw_project_for_user(request, project_code)

    # Exchange code for access token, store it in session
    if "add_github_state" in request.session:
        state = request.session.pop("add_github_state")
        if request.GET.get("state") != state:
            return HttpResponseForbidden()

        if request.GET.get("error") == "access_denied":
            messages.warning(request, "GitHub setup was cancelled.")
            return redirect("hc-channels", project.code)

        if "code" not in request.GET:
            return HttpResponseBadRequest()

        code = request.GET["code"]
        request.session["add_github_token"] = client.get_user_access_token(code)

    if "add_github_token" not in request.session:
        return HttpResponseForbidden()

    install_url = f"{settings.GITHUB_PUBLIC_LINK}/installations/new"
    try:
        repos = client.get_repos(request.session["add_github_token"])
    except client.BadCredentials:
        messages.warning(request, "GitHub setup failed, GitHub access was revoked.")
        request.session.pop("add_github_project")
        request.session.pop("add_github_token")
        return redirect("hc-channels", project.code)

    if not repos:
        return redirect(install_url)

    ctx = {
        "repo_names": sorted(repos.keys()),
        "project": project,
        "install_url": install_url,
    }
    return render(request, "add_github_form.html", ctx)


@require_setting("GITHUB_CLIENT_ID")
@login_required
@require_POST
def save(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    if "add_github_token" not in request.session:
        return HttpResponseForbidden()

    token = request.session.pop("add_github_token")
    request.session.pop("add_github_project")

    form = forms.AddGitHubForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest()

    try:
        # Fetch user's available repos from GitHub again, to make sure the user
        # still has access to the repo we are about to use in the integration.
        repos = client.get_repos(token)
    except client.BadCredentials:
        messages.warning(request, "GitHub setup failed, GitHub access was revoked.")
        return redirect("hc-channels", project.code)

    repo_name = form.cleaned_data["repo_name"]
    if repo_name not in repos:
        return HttpResponseForbidden()

    channel = Channel(kind="github", project=project)
    channel.value = json.dumps(
        {
            "installation_id": repos[repo_name],
            "repo": repo_name,
            "labels": form.get_labels(),
        }
    )
    channel.name = repo_name
    channel.save()
    channel.assign_all_checks()

    messages.success(request, "Success, integration added!")
    return redirect("hc-channels", project.code)
