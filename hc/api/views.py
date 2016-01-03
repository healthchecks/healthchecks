import json

from django.contrib.humanize.templatetags.humanize import naturaltime
from django.db.models import F
from django.http import HttpResponse, HttpResponseBadRequest
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from hc.api.decorators import uuid_or_400
from hc.api.models import Check, Ping


@csrf_exempt
@uuid_or_400
def ping(request, code):
    try:
        check = Check.objects.get(code=code)
    except Check.DoesNotExist:
        return HttpResponseBadRequest()

    check.n_pings = F("n_pings") + 1
    check.last_ping = timezone.now()
    if check.status == "new":
        check.status = "up"

    check.save()
    check.refresh_from_db()

    ping = Ping(owner=check)
    headers = request.META
    ping.n = check.n_pings
    ping.remote_addr = headers.get("HTTP_X_REAL_IP", headers["REMOTE_ADDR"])
    ping.scheme = headers.get("HTTP_X_SCHEME", "http")
    ping.method = headers["REQUEST_METHOD"]
    # If User-Agent is longer than 200 characters, truncate it:
    ping.ua = headers.get("HTTP_USER_AGENT", "")[:200]
    ping.save()

    response = HttpResponse("OK")
    response["Access-Control-Allow-Origin"] = "*"
    return response


@csrf_exempt
def handle_email(request):
    if request.method != "POST":
        return HttpResponseBadRequest()

    events = json.loads(request.POST["mandrill_events"])
    for event in events:
        for recipient_address, recipient_name in event["msg"]["to"]:
            code, domain = recipient_address.split("@")
            try:
                check = Check.objects.get(code=code)
            except ValueError:
                continue
            except Check.DoesNotExist:
                continue

            check.n_pings = F("n_pings") + 1
            check.last_ping = timezone.now()
            if check.status == "new":
                check.status = "up"

            check.save()

            ping = Ping(owner=check)
            ping.scheme = "email"
            ping.save()

    response = HttpResponse("OK")
    return response


@uuid_or_400
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
