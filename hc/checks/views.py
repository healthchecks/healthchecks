from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone

from hc.checks.models import Canary


def ping(request, code):
    try:
        canary = Canary.objects.get(code=code)
    except Canary.DoesNotExist:
        return HttpResponseBadRequest()

    canary.last_ping = timezone.now()
    canary.save()

    return HttpResponse()
