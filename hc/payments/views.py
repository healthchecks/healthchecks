from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse


def pricing(request, code=None):
    # FIXME: placeholder for a public "Pricing" page
    return HttpResponse("not implemented")


@login_required
def billing(request):
    # FIXME: placeholder for a "Billing Settings" page
    return HttpResponse("not implemented")
