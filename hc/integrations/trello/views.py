from __future__ import annotations

import logging
from urllib.parse import urlencode
from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST
from hc.accounts.http import AuthenticatedHttpRequest
from hc.api.models import Channel
from hc.front.decorators import require_setting
from hc.front.views import _get_rw_project_for_user
from hc.integrations.trello.forms import AddTrelloForm
from hc.lib import curl
from hc.lib.urls import absolute_reverse
from pydantic import BaseModel, TypeAdapter, ValidationError

logger = logging.getLogger(__name__)


@require_setting("TRELLO_APP_KEY")
@login_required
def add(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = AddTrelloForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        channel = Channel(project=project, kind="trello")
        channel.value = form.get_value()
        channel.save()

        channel.assign_all_checks()
        return redirect("hc-channels", project.code)

    return_url = absolute_reverse("hc-add-trello", args=[project.code])
    authorize_url = "https://trello.com/1/authorize?" + urlencode(
        {
            "expiration": "never",
            "name": settings.SITE_NAME,
            "scope": "read,write",
            "response_type": "token",
            "key": settings.TRELLO_APP_KEY,
            "return_url": return_url,
        }
    )

    ctx = {
        "page": "channels",
        "project": project,
        "authorize_url": authorize_url,
    }

    return render(request, "add_trello.html", ctx)


class TrelloList(BaseModel):
    id: str
    name: str


class TrelloBoard(BaseModel):
    id: str
    name: str
    lists: list[TrelloList]


TrelloBoards = TypeAdapter(list[TrelloBoard])


@require_setting("TRELLO_APP_KEY")
@login_required
@require_POST
def trello_settings(request: AuthenticatedHttpRequest) -> HttpResponse:
    token = request.POST.get("token", "")

    url = "https://api.trello.com/1/members/me/boards"
    assert settings.TRELLO_APP_KEY
    params = {
        "key": settings.TRELLO_APP_KEY,
        "token": token,
        "filter": "open",
        "fields": "id,name",
        "lists": "open",
        "list_fields": "id,name",
    }

    result = curl.get(url, params)
    try:
        boards = TrelloBoards.validate_json(result.content)
    except ValidationError:
        logger.warning("Unexpected Trello API response: %s", result.content)
        return render(request, "trello_settings.html", {"error": 1})

    num_lists = sum(len(board.lists) for board in boards)
    ctx = {"token": token, "boards": boards, "num_lists": num_lists}
    return render(request, "trello_settings.html", ctx)
