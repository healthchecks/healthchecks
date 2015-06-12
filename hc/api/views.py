from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone

from hc.api.models import Check


def ping(request, code):
    try:
        check = Check.objects.get(code=code)
    except Check.DoesNotExist:
        return HttpResponseBadRequest()

    check.last_ping = timezone.now()
    check.save()

    return HttpResponse()
