from datetime import timedelta as td
import time

from django.conf import settings
from django.db import connection
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from hc.accounts.models import Profile
from hc.api import schemas
from hc.api.decorators import authorize, authorize_read, cors, validate_json
from hc.api.forms import FlipsFiltersForm
from hc.api.models import MAX_DELTA, Flip, Channel, Check, Notification, Ping
from hc.lib.badges import check_signature, get_badge_svg, get_badge_url


class BadChannelException(Exception):
    def __init__(self, message):
        self.message = message


@csrf_exempt
@never_cache
def ping(request, code, check=None, action="success", exitstatus=None):
    if check is None:
        try:
            check = Check.objects.get(code=code)
        except Check.DoesNotExist:
            return HttpResponseNotFound("not found")

    if exitstatus is not None and exitstatus > 255:
        return HttpResponseBadRequest("invalid url format")

    headers = request.META
    remote_addr = headers.get("HTTP_X_FORWARDED_FOR", headers["REMOTE_ADDR"])
    remote_addr = remote_addr.split(",")[0]
    scheme = headers.get("HTTP_X_FORWARDED_PROTO", "http")
    method = headers["REQUEST_METHOD"]
    ua = headers.get("HTTP_USER_AGENT", "")
    body = request.body[: settings.PING_BODY_LIMIT]

    if exitstatus is not None and exitstatus > 0:
        action = "fail"

    if check.methods == "POST" and method != "POST":
        action = "ign"

    check.ping(remote_addr, scheme, method, ua, body, action, exitstatus)

    response = HttpResponse("OK")
    if settings.PING_BODY_LIMIT is not None:
        response["Ping-Body-Limit"] = str(settings.PING_BODY_LIMIT)
    response["Access-Control-Allow-Origin"] = "*"
    return response


@csrf_exempt
def ping_by_slug(request, ping_key, slug, action="success", exitstatus=None):
    try:
        check = Check.objects.get(slug=slug, project__ping_key=ping_key)
    except Check.DoesNotExist:
        return HttpResponseNotFound("not found")
    except Check.MultipleObjectsReturned:
        return HttpResponse("ambiguous slug", status=409)

    return ping(request, check.code, check, action, exitstatus)


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
    # First, validate the supplied channel codes/names
    if "channels" not in spec:
        # If the channels key is not present, don't update check's channels
        new_channels = None
    elif spec["channels"] == "*":
        # "*" means "all project's channels"
        new_channels = Channel.objects.filter(project=check.project)
    elif spec.get("channels") == "":
        # "" means "empty list"
        new_channels = []
    else:
        # expect a comma-separated list of channel codes or names
        new_channels = set()
        available = list(Channel.objects.filter(project=check.project))

        for s in spec["channels"].split(","):
            if s == "":
                raise BadChannelException("empty channel identifier")

            matches = [c for c in available if str(c.code) == s or c.name == s]
            if len(matches) == 0:
                raise BadChannelException("invalid channel identifier: %s" % s)
            elif len(matches) > 1:
                raise BadChannelException("non-unique channel identifier: %s" % s)

            new_channels.add(matches[0])

    need_save = False
    if check.pk is None:
        # Empty pk means we're inserting a new check,
        # and so do need to save() it:
        need_save = True

    if "name" in spec and check.name != spec["name"]:
        check.set_name_slug(spec["name"])
        need_save = True

    if "timeout" in spec and "schedule" not in spec:
        new_timeout = td(seconds=spec["timeout"])
        if check.kind != "simple" or check.timeout != new_timeout:
            check.kind = "simple"
            check.timeout = new_timeout
            need_save = True

    if "grace" in spec:
        new_grace = td(seconds=spec["grace"])
        if check.grace != new_grace:
            check.grace = new_grace
            need_save = True

    if "schedule" in spec:
        if check.kind != "cron" or check.schedule != spec["schedule"]:
            check.kind = "cron"
            check.schedule = spec["schedule"]
            need_save = True

    if "subject" in spec:
        check.success_kw = spec["subject"]
        check.filter_subject = bool(check.success_kw or check.failure_kw)
        need_save = True

    if "subject_fail" in spec:
        check.failure_kw = spec["subject_fail"]
        check.filter_subject = bool(check.success_kw or check.failure_kw)
        need_save = True

    for key in (
        "tags",
        "desc",
        "manual_resume",
        "methods",
        "tz",
        "success_kw",
        "failure_kw",
        "filter_subject",
        "filter_body",
    ):
        if key in spec and getattr(check, key) != spec[key]:
            setattr(check, key, spec[key])
            need_save = True

    if need_save:
        check.alert_after = check.going_down_after()
        check.save()

    # This needs to be done after saving the check, because of
    # the M2M relation between checks and channels:
    if new_channels is not None:
        check.channel_set.set(new_channels)


@authorize_read
def get_checks(request):
    q = Check.objects.filter(project=request.project)
    if not request.readonly:
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
        return JsonResponse({"error": e.message}, status=400)

    return JsonResponse(check.to_dict(), status=201 if created else 200)


@csrf_exempt
@cors("GET", "POST")
def checks(request):
    if request.method == "POST":
        return create_check(request)

    return get_checks(request)


@cors("GET")
@csrf_exempt
@authorize
def channels(request):
    q = Channel.objects.filter(project=request.project)
    channels = [ch.to_dict() for ch in q]
    return JsonResponse({"channels": channels})


@authorize_read
def get_check(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
        return HttpResponseForbidden()
    return JsonResponse(check.to_dict(readonly=request.readonly))


@cors("GET")
@csrf_exempt
@authorize_read
def get_check_by_unique_key(request, unique_key):
    checks = Check.objects.filter(project=request.project.id)
    for check in checks:
        if check.unique_key == unique_key:
            return JsonResponse(check.to_dict(readonly=request.readonly))
    return HttpResponseNotFound()


@validate_json(schemas.check)
@authorize
def update_check(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    try:
        _update(check, request.json)
    except BadChannelException as e:
        return JsonResponse({"error": e.message}, status=400)

    return JsonResponse(check.to_dict())


@authorize
def delete_check(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
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
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    # Track the status change for correct downtime calculation in Check.downtimes()
    check.create_flip("paused", mark_as_processed=True)

    check.status = "paused"
    check.last_start = None
    check.alert_after = None
    check.save()

    # After pausing a check we must check if all checks are up,
    # and Profile.next_nag_date needs to be cleared out:
    check.project.update_next_nag_dates()

    return JsonResponse(check.to_dict())


@cors("POST")
@csrf_exempt
@validate_json()
@authorize
def resume(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    if check.status != "paused":
        return HttpResponse("check is not paused", status=409)

    check.create_flip("new", mark_as_processed=True)

    check.status = "new"
    check.last_start = None
    check.last_ping = None
    check.alert_after = None
    check.save()

    return JsonResponse(check.to_dict())


@cors("GET")
@csrf_exempt
@validate_json()
@authorize
def pings(request, code):
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    # Look up ping log limit from account's profile.
    # There might be more pings in the database (depends on how pruning is handled)
    # but we will not return more than the limit allows.
    profile = Profile.objects.get(user__project=request.project)
    limit = profile.ping_log_limit

    # Query in descending order so we're sure to get the most recent
    # pings, regardless of the limit restriction
    pings = Ping.objects.filter(owner=check).order_by("-id")[:limit]

    # Ascending order is more convenient for calculating duration, so use reverse()
    prev, dicts = None, []
    for ping in reversed(pings):
        d = ping.to_dict()
        if ping.kind != "start" and prev and prev.kind == "start":
            delta = ping.created - prev.created
            if delta < MAX_DELTA:
                d["duration"] = delta.total_seconds()

        dicts.insert(0, d)
        prev = ping

    return JsonResponse({"pings": dicts})


def flips(request, check):
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    form = FlipsFiltersForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest()

    flips = Flip.objects.filter(owner=check).order_by("-id")

    if form.cleaned_data["start"]:
        flips = flips.filter(created__gte=form.cleaned_data["start"])

    if form.cleaned_data["end"]:
        flips = flips.filter(created__lt=form.cleaned_data["end"])

    if form.cleaned_data["seconds"]:
        threshold = timezone.now() - td(seconds=form.cleaned_data["seconds"])
        flips = flips.filter(created__gte=threshold)

    return JsonResponse({"flips": [flip.to_dict() for flip in flips]})


@cors("GET")
@csrf_exempt
@authorize_read
def flips_by_uuid(request, code):
    check = get_object_or_404(Check, code=code)
    return flips(request, check)


@cors("GET")
@csrf_exempt
@authorize_read
def flips_by_unique_key(request, unique_key):
    checks = Check.objects.filter(project=request.project.id)
    for check in checks:
        if check.unique_key == unique_key:
            return flips(request, check)
    return HttpResponseNotFound()


@cors("GET")
@csrf_exempt
@authorize_read
def badges(request):
    tags = set(["*"])
    for check in Check.objects.filter(project=request.project):
        tags.update(check.tags_list())

    key = request.project.badge_key
    badges = {}
    for tag in tags:
        badges[tag] = {
            "svg": get_badge_url(key, tag),
            "svg3": get_badge_url(key, tag, with_late=True),
            "json": get_badge_url(key, tag, fmt="json"),
            "json3": get_badge_url(key, tag, fmt="json", with_late=True),
            "shields": get_badge_url(key, tag, fmt="shields"),
            "shields3": get_badge_url(key, tag, fmt="shields", with_late=True),
        }

    return JsonResponse({"badges": badges})


@never_cache
@cors("GET")
def badge(request, badge_key, signature, tag, fmt):
    if fmt not in ("svg", "json", "shields"):
        return HttpResponseNotFound()

    with_late = True
    if len(signature) == 10 and signature.endswith("-2"):
        with_late = False

    if not check_signature(badge_key, tag, signature):
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
        check_status = check.get_status()

        if check_status == "down":
            down += 1
            status = "down"
            if fmt == "svg":
                # For SVG badges, we can leave the loop as soon as we
                # find the first "down"
                break
        elif check_status == "grace":
            grace += 1
            if status == "up" and with_late:
                status = "late"

    if fmt == "shields":
        color = "success"
        if status == "down":
            color = "critical"
        elif status == "late":
            color = "important"

        return JsonResponse(
            {"schemaVersion": 1, "label": label, "message": status, "color": color}
        )

    if fmt == "json":
        return JsonResponse(
            {"status": status, "total": total, "grace": grace, "down": down}
        )

    svg = get_badge_svg(label, status)
    return HttpResponse(svg, content_type="image/svg+xml")


@csrf_exempt
@require_POST
def notification_status(request, code):
    """Handle notification delivery status callbacks."""

    try:
        cutoff = timezone.now() - td(hours=1)
        notification = Notification.objects.get(code=code, created__gt=cutoff)
    except Notification.DoesNotExist:
        # If the notification does not exist, or is more than a hour old,
        # return HTTP 200 so the other party doesn't retry over and over again:
        return HttpResponse()

    error, mark_disabled = None, False

    # Look for "error" and "mark_disabled" keys:
    if request.POST.get("error"):
        error = request.POST["error"][:200]
        mark_disabled = request.POST.get("mark_disabled")

    # Handle "MessageStatus" key from Twilio
    if request.POST.get("MessageStatus") in ("failed", "undelivered"):
        status = request.POST["MessageStatus"]
        error = f"Delivery failed (status={status})."

    # Handle "CallStatus" key from Twilio
    if request.POST.get("CallStatus") == "failed":
        error = "Delivery failed (status=failed)."

    if error:
        notification.error = error
        notification.save(update_fields=["error"])

        channel_q = Channel.objects.filter(id=notification.channel_id)
        channel_q.update(last_error=error)
        if mark_disabled:
            channel_q.update(disabled=True)

    return HttpResponse()


def metrics(request):
    if not settings.METRICS_KEY:
        return HttpResponseForbidden()

    key = request.META.get("HTTP_X_METRICS_KEY")
    if key != settings.METRICS_KEY:
        return HttpResponseForbidden()

    doc = {
        "ts": int(time.time()),
        "max_ping_id": Ping.objects.values_list("id", flat=True).last(),
        "max_notification_id": Notification.objects.values_list("id", flat=True).last(),
        "num_unprocessed_flips": Flip.objects.filter(processed__isnull=True).count(),
    }

    return JsonResponse(doc)


def status(request):
    with connection.cursor() as c:
        c.execute("SELECT 1")
        c.fetchone()

    return HttpResponse("OK")
