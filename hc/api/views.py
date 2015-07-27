import json

from django.contrib.humanize.templatetags.humanize import naturaltime
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from hc.api.models import Check, Ping


@csrf_exempt
def ping(request, code):
    try:
        check = Check.objects.get(code=code)
    except Check.DoesNotExist:
        return HttpResponseBadRequest()

    check.last_ping = timezone.now()
    if check.status == "new":
        check.status = "up"

    check.save()

    ping = Ping(owner=check)
    headers = request.META
    ping.remote_addr = headers.get("X_REAL_IP", headers["REMOTE_ADDR"])
    ping.method = headers["REQUEST_METHOD"]
    ping.ua = headers.get("HTTP_USER_AGENT", "")
    ping.body = request.body
    ping.save()

    response = HttpResponse("OK")
    response["Access-Control-Allow-Origin"] = "*"
    return response


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
