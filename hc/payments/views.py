from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse


def pricing(request: HttpRequest, code: UUID | None = None) -> HttpResponse:
    # FIXME: placeholder for a public "Pricing" page
    return HttpResponse("not implemented")


@login_required
def billing(request: HttpRequest) -> HttpResponse:
    # FIXME: placeholder for a "Billing Settings" page
    return HttpResponse("not implemented")
