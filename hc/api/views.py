from datetime import timedelta as td
import uuid

from django.conf import settings
from django.db import connection
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from hc.api import schemas
from hc.api.decorators import authorize, authorize_read, cors, validate_json
from hc.api.models import Check, Notification, Channel
from hc.lib.badges import check_signature, get_badge_svg
from hc.lib.jsonschema import ValidationError, validate


class BadChannelException(Exception):
    pass


@csrf_exempt
@never_cache
def ping(request, code, action="success"):
    check = get_object_or_404(Check, code=code)

    headers = request.META
    remote_addr = headers.get("HTTP_X_FORWARDED_FOR", headers["REMOTE_ADDR"])
    remote_addr = remote_addr.split(",")[0]
    scheme = headers.get("HTTP_X_FORWARDED_PROTO", "http")
    method = headers["REQUEST_METHOD"]
    ua = headers.get("HTTP_USER_AGENT", "")
    body = request.body.decode()

    if check.methods == "POST" and method != "POST":
        action = "ign"

    check.ping(remote_addr, scheme, method, ua, body, action)

    response = HttpResponse("OK")
    response["Access-Control-Allow-Origin"] = "*"
    return response


def _lookup(project, spec):
    unique_fields = spec.get("unique", [])
    if unique_fields:
        existing_checks = Check.objects.filter(project=project)
        if "name" in unique_fields:
            existing_checks = existing_checks.filter(name=spec.get("name"))
        if "tags" in unique_fields:
            existing_checks = existing_checks.filter(tags=spec.get("tags"))
        if "timeout" in unique_fields:
            timeout = td(seconds=spec["timeout"])
            existing_checks = existing_checks.filter(timeout=timeout)
        if "grace" in unique_fields:
            grace = td(seconds=spec["grace"])
            existing_checks = existing_checks.filter(grace=grace)

        return existing_checks.first()


def _update(check, spec):
    channels = set()
    # First, validate the supplied channel codes
    if "channels" in spec and spec["channels"] not in ("*", ""):
        q = Channel.objects.filter(project=check.project)
        for s in spec["channels"].split(","):
            try:
                code = uuid.UUID(s)
            except ValueError:
                raise BadChannelException("invalid channel identifier: %s" % s)

            try:
                channels.add(q.get(code=code))
            except Channel.DoesNotExist:
                raise BadChannelException("invalid channel identifier: %s" % s)

    if "name" in spec:
        check.name = spec["name"]

    if "tags" in spec:
        check.tags = spec["tags"]

    if "desc" in spec:
        check.desc = spec["desc"]

    if "timeout" in spec and "schedule" not in spec:
        check.kind = "simple"
        check.timeout = td(seconds=spec["timeout"])

    if "grace" in spec:
        check.grace = td(seconds=spec["grace"])

    if "schedule" in spec:
        check.kind = "cron"
        check.schedule = spec["schedule"]
        if "tz" in spec:
            check.tz = spec["tz"]

    check.alert_after = check.going_down_after()
    check.save()

    # This needs to be done after saving the check, because of
    # the M2M relation between checks and channels:
    if spec.get("channels") == "*":
        check.assign_all_channels()
    elif spec.get("channels") == "":
        check.channel_set.clear()
    elif channels:
        check.channel_set.set(channels)

    return check


@validate_json()
@authorize_read
def get_checks(request):
    q = Check.objects.filter(project=request.project)
    q = q.prefetch_related("channel_set")

    tags = set(request.GET.getlist("tag"))
    for tag in tags:
        # approximate filtering by tags
        q = q.filter(tags__contains=tag)

    checks = []
    for check in q:
        # precise, final filtering
        if not tags or check.matches_tag_set(tags):
            checks.append(check.to_dict(readonly=request.readonly))

    return JsonResponse({"checks": checks})


@validate_json(schemas.check)
@authorize
def create_check(request):
    created = False
    check = _lookup(request.project, request.json)
    if check is None:
        if request.project.num_checks_available() <= 0:
            return HttpResponseForbidden()

        check = Check(project=request.project)
        created = True

    try:
        _update(check, request.json)
    except BadChannelException as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(check.to_dict(), status=201 if created else 200)


@csrf_exempt
@cors("GET", "POST")
def checks(request):
    if request.method == "POST":
        return create_check(request)

    return get_checks(request)


@cors("GET")
@validate_json()
@authorize
def channels(request):
    q = Channel.objects.filter(project=request.project)
    channels = [ch.to_dict() for ch in q]
    return JsonResponse({"channels": channels})


@validate_json()
@authorize_read
def get_check(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project != request.project:
        return HttpResponseForbidden()

    if 'history' in request.GET:
        return JsonResponse(check.to_dict(readonly=request.readonly, history=request.GET['history']))
    return JsonResponse(check.to_dict(readonly=request.readonly))


@validate_json(schemas.check)
@authorize
def update_check(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project != request.project:
        return HttpResponseForbidden()

    try:
        _update(check, request.json)
    except BadChannelException as e:
        return JsonResponse({"error": str(e)}, status=400)

    return JsonResponse(check.to_dict())


@validate_json()
@authorize
def delete_check(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project != request.project:
        return HttpResponseForbidden()

    response = check.to_dict()
    check.delete()
    return JsonResponse(response)


@csrf_exempt
@cors("POST", "DELETE", "GET")
def single(request, code):
    if request.method == "POST":
        return update_check(request, code)

    if request.method == "DELETE":
        return delete_check(request, code)

    return get_check(request, code)


@cors("POST")
@csrf_exempt
@validate_json()
@authorize
def pause(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project != request.project:
        return HttpResponseForbidden()

    check.status = "paused"
    check.last_start = None
    check.alert_after = None
    check.save()
    return JsonResponse(check.to_dict())


@never_cache
@cors("GET")
def badge(request, badge_key, signature, tag, fmt="svg"):
    if not check_signature(badge_key, tag, signature):
        return HttpResponseNotFound()

    if fmt not in ("svg", "json", "shields"):
        return HttpResponseNotFound()

    q = Check.objects.filter(project__badge_key=badge_key)
    if tag != "*":
        q = q.filter(tags__contains=tag)
        label = tag
    else:
        label = settings.MASTER_BADGE_LABEL

    status, total, grace, down = "up", 0, 0, 0
    for check in q:
        if tag != "*" and tag not in check.tags_list():
            continue

        total += 1
        check_status = check.get_status(with_started=False)

        if check_status == "down":
            down += 1
            status = "down"
            if fmt == "svg":
                # For SVG badges, we can leave the loop as soon as we
                # find the first "down"
                break
        elif check_status == "grace":
            grace += 1
            if status == "up":
                status = "late"

    if fmt == "shields":
        color = "success"
        if status == "down":
            color = "critical"
        elif status == "late":
            color = "important"

        return JsonResponse({"label": label, "message": status, "color": color})

    if fmt == "json":
        return JsonResponse(
            {"status": status, "total": total, "grace": grace, "down": down}
        )

    svg = get_badge_svg(label, status)
    return HttpResponse(svg, content_type="image/svg+xml")


@csrf_exempt
@require_POST
def bounce(request, code):
    notification = get_object_or_404(Notification, code=code)

    # If webhook is more than 10 minutes late, don't accept it:
    td = timezone.now() - notification.created
    if td.total_seconds() > 600:
        return HttpResponseForbidden()

    notification.error = request.body.decode()[:200]
    notification.save()

    notification.channel.last_error = notification.error
    if request.GET.get("type") in (None, "Permanent"):
        # For permanent bounces, mark the channel as not verified, so we
        # will not try to deliver to it again.
        notification.channel.email_verified = False

    notification.channel.save()

    return HttpResponse()


def status(request):
    with connection.cursor() as c:
        c.execute("SELECT 1")
        c.fetchone()

    return HttpResponse("OK")
