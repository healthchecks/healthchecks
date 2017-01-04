from datetime import timedelta as td

from django.db.models import F
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt

from hc.api import schemas
from hc.api.decorators import check_api_key, uuid_or_400, validate_json
from hc.api.models import Check, Ping
from hc.lib.badges import check_signature, get_badge_svg


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
    check.alert_after = check.get_alert_after()
    if check.status in ("new", "paused"):
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


def _create_check(user, spec):
    check = Check(user=user)
    check.name = spec.get("name", "")
    check.tags = spec.get("tags", "")

    if "timeout" in spec and "schedule" not in spec:
        check.timeout = td(seconds=spec["timeout"])

    if "grace" in spec:
        check.grace = td(seconds=spec["grace"])

    if "schedule" in spec:
        check.kind = "cron"
        check.schedule = spec["schedule"]
        if "tz" in spec and "schedule" in spec:
            check.tz = spec["tz"]

    unique_fields = spec.get("unique", [])
    if unique_fields:
        existing_checks = Check.objects.filter(user=user)
        if "name" in unique_fields:
            existing_checks = existing_checks.filter(name=check.name)
        if "tags" in unique_fields:
            existing_checks = existing_checks.filter(tags=check.tags)
        if "timeout" in unique_fields:
            existing_checks = existing_checks.filter(timeout=check.timeout)
        if "grace" in unique_fields:
            existing_checks = existing_checks.filter(grace=check.grace)

        if existing_checks.count() > 0:
            # There might be more than one matching check, return first
            first_match = existing_checks.first()
            return JsonResponse(first_match.to_dict(), status=200)

    check.save()

    # This needs to be done after saving the check, because of
    # the M2M relation between checks and channels:
    if spec.get("channels") == "*":
        check.assign_all_channels()

    return JsonResponse(check.to_dict(), status=201)


@csrf_exempt
@check_api_key
@validate_json(schemas.check)
def checks(request):
    if request.method == "GET":
        q = Check.objects.filter(user=request.user)
        doc = {"checks": [check.to_dict() for check in q]}
        return JsonResponse(doc)

    elif request.method == "POST":
        return _create_check(request.user, request.json)

    # If request is neither GET nor POST, return "405 Method not allowed"
    return HttpResponse(status=405)


@csrf_exempt
@check_api_key
def pause(request, code):
    if request.method != "POST":
        # Method not allowed
        return HttpResponse(status=405)

    try:
        check = Check.objects.get(code=code, user=request.user)
    except Check.DoesNotExist:
        return HttpResponseBadRequest()

    check.status = "paused"
    check.save()
    return JsonResponse(check.to_dict())


@never_cache
def badge(request, username, signature, tag):
    if not check_signature(username, tag, signature):
        return HttpResponseBadRequest()

    status = "up"
    q = Check.objects.filter(user__username=username, tags__contains=tag)
    for check in q:
        if tag not in check.tags_list():
            continue

        if status == "up" and check.in_grace_period():
            status = "late"

        if check.get_status() == "down":
            status = "down"
            break

    svg = get_badge_svg(tag, status)
    return HttpResponse(svg, content_type="image/svg+xml")
