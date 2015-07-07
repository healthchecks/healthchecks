import json

from django.contrib.humanize.templatetags.humanize import naturaltime
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone

from hc.api.models import Check


def ping(request, code):
    try:
        check = Check.objects.get(code=code)
    except Check.DoesNotExist:
        return HttpResponseBadRequest()

    check.last_ping = timezone.now()
    if check.status == "new":
        check.status = "up"

    check.save()

    return HttpResponse("OK")


def status(request, code):
    response = {
        "last_ping": None,
        "last_ping_human": None,
        "secs_to_alert": None
    }

    check = Check.objects.get(code=code)

    if check.last_ping and check.alert_after:
        response["last_ping"] = check.last_ping.isoformat()
        response["last_ping_human"] = naturaltime(check.last_ping)

        duration = check.alert_after - timezone.now()
        response["secs_to_alert"] = int(duration.total_seconds())

    return HttpResponse(json.dumps(response),
                        content_type="application/javascript")
