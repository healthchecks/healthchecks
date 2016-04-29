from datetime import timedelta as td

from django.db.models import F
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from hc.api import schemas
from hc.api.decorators import check_api_key, uuid_or_400, validate_json
from hc.api.models import Check, Ping


@csrf_exempt
@uuid_or_400
@never_cache
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
    remote_addr = headers.get("HTTP_X_FORWARDED_FOR", headers["REMOTE_ADDR"])
    ping.remote_addr = remote_addr.split(",")[0]
    ping.scheme = headers.get("HTTP_X_FORWARDED_PROTO", "http")
    ping.method = headers["REQUEST_METHOD"]
    # If User-Agent is longer than 200 characters, truncate it:
    ping.ua = headers.get("HTTP_USER_AGENT", "")[:200]
    ping.save()

    response = HttpResponse("OK")
    response["Access-Control-Allow-Origin"] = "*"
    return response


@csrf_exempt
@check_api_key
@validate_json(schemas.check)
def create_check(request):
    if request.method == "GET":
        code = 200
        response = {
            "checks": [{
                "name": check.name,
                "ping_url": check.url(),
                "tags": check.tags,
                "timeout": int(check.timeout.total_seconds()),
                "grace": int(check.grace.total_seconds()),
                # "channels": check.channels,
            } for check in Check.objects.filter(user=request.user)]
        }
    elif request.method == "POST":
        check = Check(user=request.user)
        check.name = str(request.json.get("name", ""))
        check.tags = str(request.json.get("tags", ""))
        if "timeout" in request.json:
            check.timeout = td(seconds=request.json["timeout"])
        if "grace" in request.json:
            check.grace = td(seconds=request.json["grace"])

        check.save()

        # This needs to be done after saving the check, because of
        # the M2M relation between checks and channels:
        if request.json.get("channels") == "*":
            check.assign_all_channels()

        code = 201
        response = {
            "ping_url": check.url()
        }
    else:
        return HttpResponse(status=405)

    return JsonResponse(response, status=code)
