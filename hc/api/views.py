from __future__ import annotations

import email.policy
import time
from collections.abc import Iterable
from datetime import datetime
from datetime import timedelta as td
from datetime import timezone
from email import message_from_bytes
from typing import Any, Literal
from uuid import UUID

from cronsim import CronSim, CronSimError
from django.conf import settings
from django.core.signing import BadSignature
from django.db import connection, transaction
from django.db.models import Prefetch
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.utils.timezone import now
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from oncalendar import OnCalendar, OnCalendarError
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator
from pydantic_core import PydanticCustomError

from hc.accounts.models import Profile, Project
from hc.api.decorators import ApiRequest, authorize, authorize_read, cors
from hc.api.forms import FlipsFiltersForm
from hc.api.models import MAX_DURATION, Channel, Check, Flip, Notification, Ping
from hc.lib.badges import check_signature, get_badge_svg, get_badge_url
from hc.lib.signing import unsign_bounce_id
from hc.lib.string import is_valid_uuid_string
from hc.lib.tz import all_timezones


class BadChannelException(Exception):
    def __init__(self, message: str):
        self.message = message


def guess_kind(schedule: str) -> str:
    # If it is a single line with 5 components, it is probably a cron expression:
    if "\n" not in schedule.strip() and len(schedule.split()) == 5:
        return "cron"

    return "oncalendar"


class Spec(BaseModel):
    channels: str | None = None
    desc: str | None = None
    failure_kw: str | None = Field(None, max_length=200)
    filter_body: bool | None = None
    filter_subject: bool | None = None
    grace: td | None = Field(None, ge=60, le=31536000)
    manual_resume: bool | None = None
    methods: Literal["", "POST"] | None = None
    name: str | None = Field(None, max_length=100)
    schedule: str | None = Field(None, max_length=100)
    slug: str | None = Field(None, pattern="^[a-z0-9-_]*$")
    start_kw: str | None = Field(None, max_length=200)
    subject: str | None = Field(None, max_length=200)
    subject_fail: str | None = Field(None, max_length=200)
    success_kw: str | None = Field(None, max_length=200)
    tags: str | None = None
    timeout: td | None = Field(None, ge=60, le=31536000)
    tz: str | None = None
    unique: list[Literal["name", "slug", "tags", "timeout", "grace"]] | None = None

    @model_validator(mode="before")
    @classmethod
    def check_nulls(cls, data: dict[str, Any]) -> dict[str, Any]:
        # Look for any null values in the incoming data. Replace them with a
        # float. None of the fields have a float type, and we are using
        # strict validation, so this will cause type validation to fail.
        for k, v in data.items():
            if v is None:
                data[k] = float()
        return data

    @field_validator("timeout", "grace", mode="before")
    @classmethod
    def convert_to_timedelta(cls, v: Any) -> Any:
        if isinstance(v, int):
            return td(seconds=v)
        return v

    @field_validator("tz")
    @classmethod
    def check_tz(cls, v: str) -> str:
        if v not in all_timezones:
            raise PydanticCustomError("tz_syntax", "not a valid timezone")
        return v

    @field_validator("schedule")
    @classmethod
    def check_schedule(cls, v: str) -> str:
        if guess_kind(v) == "cron":
            try:
                # Test if cronsim accepts it and can calculate the next datetime
                it = CronSim(v, datetime(2000, 1, 1))
                next(it)
            except (CronSimError, StopIteration):
                raise PydanticCustomError("cron_syntax", "not a valid cron expression")
        else:
            try:
                # Test if oncalendar accepts it, and can calculate the next datetime
                oncalendar_it = OnCalendar(v, datetime(2000, 1, 1, tzinfo=timezone.utc))
                next(oncalendar_it)
            except (OnCalendarError, StopIteration):
                raise PydanticCustomError("cron_syntax", "not a valid expression")

        return v

    def kind(self) -> str | None:
        if self.schedule:
            return guess_kind(self.schedule)

        if self.timeout:
            return "simple"

        return None


CUSTOM_ERRORS = {
    "too_long": "%s is too long",
    "string_too_long": "%s is too long",
    "string_type": "%s is not a string",
    "string_pattern_mismatch": "%s does not match pattern",
    "less_than_equal": "%s is too large",
    "greater_than_equal": "%s is too small",
    "int_type": "%s is not a number",
    "bool_type": "%s is not a boolean",
    "literal_error": "%s has unexpected value",
    "list_type": "%s is not an array",
    "cron_syntax": "%s is not a valid cron or OnCalendar expression",
    "tz_syntax": "%s is not a valid timezone",
    "time_delta_type": "%s is not a number",
}


def format_first_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    subject = first_error["loc"][0]
    if len(first_error["loc"]) == 2:
        subject = f"an item in '{subject}'"

    tmpl = CUSTOM_ERRORS[first_error["type"]]
    return "json validation error: " + tmpl % subject


@csrf_exempt
@never_cache
def ping(
    request: HttpRequest,
    code: UUID,
    check: Check | None = None,
    action: str = "success",
    exitstatus: int | None = None,
) -> HttpResponse:
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
    if "." in remote_addr and ":" in remote_addr:
        # If remote_addr is in a ipv4address:port format (like in Azure App Service),
        # remove the port:
        remote_addr = remote_addr.split(":")[0]

    scheme = headers.get("HTTP_X_FORWARDED_PROTO", "http")
    method = headers["REQUEST_METHOD"]
    ua = headers.get("HTTP_USER_AGENT", "")
    body = request.body[: settings.PING_BODY_LIMIT]

    if exitstatus is not None and exitstatus > 0:
        action = "fail"

    if check.methods == "POST" and method != "POST":
        action = "ign"

    rid, rid_str = None, request.GET.get("rid")
    if rid_str is not None:
        if not is_valid_uuid_string(rid_str):
            return HttpResponseBadRequest("invalid uuid format")
        rid = UUID(rid_str)

    check.ping(remote_addr, scheme, method, ua, body, action, rid, exitstatus)

    response = HttpResponse("OK")
    if settings.PING_BODY_LIMIT is not None:
        response["Ping-Body-Limit"] = str(settings.PING_BODY_LIMIT)
    response["Access-Control-Allow-Origin"] = "*"
    return response


@csrf_exempt
def ping_by_slug(
    request: HttpRequest,
    ping_key: str,
    slug: str,
    action: str = "success",
    exitstatus: int | None = None,
) -> HttpResponse:
    created = False
    try:
        check = Check.objects.get(slug=slug, project__ping_key=ping_key)
    except Check.DoesNotExist:
        if request.GET.get("create") != "1":
            return HttpResponseNotFound("not found")

        try:
            project = Project.objects.get(ping_key=ping_key)
        except Project.DoesNotExist:
            return HttpResponseNotFound("not found")
        check = Check(project=project, name=slug, slug=slug)
        check.save()
        check.assign_all_channels()
        created = True
    except Check.MultipleObjectsReturned:
        return HttpResponse("ambiguous slug", status=409)

    response = ping(request, check.code, check, action, exitstatus)
    if response.status_code == 200 and created:
        response.content = b"Created"
        response.status_code = 201
    return response


def _lookup(project: Project, spec: Spec) -> Check | None:
    if not spec.unique:
        return None

    for field_name in spec.unique:
        # If any field referenced in 'unique' is absent then return None
        # (meaning, did not find a matching Check)
        if getattr(spec, field_name) is None:
            return None

    existing_checks = Check.objects.filter(project=project)
    if "name" in spec.unique:
        existing_checks = existing_checks.filter(name=spec.name)
    if "slug" in spec.unique:
        existing_checks = existing_checks.filter(slug=spec.slug)
    if "tags" in spec.unique:
        existing_checks = existing_checks.filter(tags=spec.tags)
    if "timeout" in spec.unique:
        existing_checks = existing_checks.filter(timeout=spec.timeout)
    if "grace" in spec.unique:
        existing_checks = existing_checks.filter(grace=spec.grace)

    return existing_checks.first()


def _update(check: Check, spec: Spec, v: int) -> None:
    new_channels: Iterable[Channel] | None
    # First, validate the supplied channel codes/names
    if spec.channels is None:
        # If the channels key is not present, don't update check's channels
        new_channels = None
    elif spec.channels == "*":
        # "*" means "all project's channels"
        new_channels = Channel.objects.filter(project=check.project)
    elif spec.channels == "":
        # "" means "empty list"
        new_channels = []
    else:
        # expect a comma-separated list of channel codes or names
        new_channels = set()
        available = list(Channel.objects.filter(project=check.project))

        for s in spec.channels.split(","):
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

    if spec.name is not None and check.name != spec.name:
        check.name = spec.name
        if v < 3:
            # v1 and v2 generates slug automatically from name
            check.slug = slugify(spec.name)
        need_save = True

    kind = spec.kind()
    if kind == "simple":
        if check.kind != "simple" or check.timeout != spec.timeout:
            check.kind = "simple"
            check.timeout = spec.timeout
            need_save = True

    if kind in ("cron", "oncalendar"):
        if check.kind != kind or check.schedule != spec.schedule:
            check.kind = kind
            assert spec.schedule is not None
            check.schedule = spec.schedule
            need_save = True

    if spec.subject is not None:
        check.success_kw = spec.subject
        check.filter_subject = bool(check.success_kw or check.failure_kw)
        need_save = True

    if spec.subject_fail is not None:
        check.failure_kw = spec.subject_fail
        check.filter_subject = bool(check.success_kw or check.failure_kw)
        need_save = True

    for key in (
        "slug",
        "tags",
        "desc",
        "manual_resume",
        "methods",
        "tz",
        "start_kw",
        "success_kw",
        "failure_kw",
        "filter_subject",
        "filter_body",
        "grace",
    ):
        v = getattr(spec, key)
        if v is not None and getattr(check, key) != v:
            setattr(check, key, v)
            need_save = True

    if need_save:
        check.alert_after = check.going_down_after()
        check.save()

    # This needs to be done after saving the check, because of
    # the M2M relation between checks and channels:
    if new_channels is not None:
        check.channel_set.set(new_channels)


@authorize_read
def get_checks(request: ApiRequest) -> JsonResponse:
    q = Check.objects.filter(project=request.project)
    if not request.readonly:
        # Use QuerySet.only() and Prefetch() to prefetch channel codes only:
        channel_q = Channel.objects.only("code")
        q = q.prefetch_related(Prefetch("channel_set", queryset=channel_q))

    tags = set(request.GET.getlist("tag"))
    for tag in tags:
        # approximate filtering by tags
        q = q.filter(tags__contains=tag)

    if slug := request.GET.get("slug"):
        q = q.filter(slug=slug)

    checks = []
    for check in q:
        # precise, final filtering
        if not tags or check.matches_tag_set(tags):
            checks.append(check.to_dict(readonly=request.readonly, v=request.v))

    return JsonResponse({"checks": checks})


@authorize
def create_check(request: ApiRequest) -> HttpResponse:
    try:
        spec = Spec.model_validate(request.json, strict=True)
    except ValidationError as e:
        return JsonResponse({"error": format_first_error(e)}, status=400)

    created = False
    check = _lookup(request.project, spec)
    if check is None:
        if request.project.num_checks_available() <= 0:
            return HttpResponseForbidden()

        check = Check(project=request.project)
        created = True

    try:
        _update(check, spec, request.v)
    except BadChannelException as e:
        return JsonResponse({"error": e.message}, status=400)

    return JsonResponse(check.to_dict(v=request.v), status=201 if created else 200)


@csrf_exempt
@cors("GET", "POST")
def checks(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        return create_check(request)

    return get_checks(request)


@cors("GET")
@csrf_exempt
@authorize
def channels(request: ApiRequest) -> JsonResponse:
    q = Channel.objects.filter(project=request.project)
    channels = [ch.to_dict() for ch in q]
    return JsonResponse({"channels": channels})


@authorize_read
def get_check(request: ApiRequest, code: UUID) -> HttpResponse:
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    return JsonResponse(check.to_dict(readonly=request.readonly, v=request.v))


@cors("GET")
@csrf_exempt
@authorize_read
def get_check_by_unique_key(request: ApiRequest, unique_key: str) -> HttpResponse:
    for check in request.project.check_set.all():
        if check.unique_key == unique_key:
            return JsonResponse(check.to_dict(readonly=request.readonly, v=request.v))
    return HttpResponseNotFound()


@authorize
def update_check(request: ApiRequest, code: UUID) -> HttpResponse:
    # Don't acquire lock right away, first see if the check exists
    # and matches the API key
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    try:
        spec = Spec.model_validate(request.json, strict=True)
    except ValidationError as e:
        return JsonResponse({"error": format_first_error(e)}, status=400)

    # Start a transaction, select for update, update.
    # Use get_object_or_404 here again, in case another concurrent request
    # has *just* deleted this check.
    with transaction.atomic():
        check = get_object_or_404(Check.objects.select_for_update(), code=code)
        try:
            _update(check, spec, request.v)
        except BadChannelException as e:
            return JsonResponse({"error": e.message}, status=400)

    return JsonResponse(check.to_dict(v=request.v))


@authorize
def delete_check(request: ApiRequest, code: UUID) -> HttpResponse:
    # Don't acquire lock right away, first see if the check exists
    # and matches the API key
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    # Start a transaction, select for update, delete.
    # Use get_object_or_404 here again, in case another concurrent request
    # has *just* deleted this check.
    with transaction.atomic():
        check = get_object_or_404(Check.objects.select_for_update(), code=code)
        check.delete()

    return JsonResponse(check.to_dict(v=request.v))


@csrf_exempt
@cors("POST", "DELETE", "GET")
def single(request: HttpRequest, code: UUID) -> HttpResponse:
    if request.method == "POST":
        return update_check(request, code)

    if request.method == "DELETE":
        return delete_check(request, code)

    return get_check(request, code)


@cors("POST")
@csrf_exempt
@authorize
def pause(request: ApiRequest, code: UUID) -> HttpResponse:
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

    return JsonResponse(check.to_dict(v=request.v))


@cors("POST")
@csrf_exempt
@authorize
def resume(request: ApiRequest, code: UUID) -> HttpResponse:
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

    return JsonResponse(check.to_dict(v=request.v))


@cors("GET")
@csrf_exempt
@authorize
def pings(request: ApiRequest, code: UUID) -> HttpResponse:
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
    pings = list(Ping.objects.filter(owner=check).order_by("-id")[:limit])

    starts: dict[UUID | None, datetime | None] = {}
    num_misses = 0
    for ping in reversed(pings):
        if ping.kind == "start":
            starts[ping.rid] = ping.created
        elif ping.kind in (None, "", "fail"):
            if ping.rid not in starts:
                # We haven't seen a start, success or fail event for this rid.
                # Will need to fall back to Ping.duration().
                num_misses += 1
            else:
                ping.duration = None
                start = starts[ping.rid]
                if start and (ping.created - start) < MAX_DURATION:
                    ping.duration = ping.created - start

            starts[ping.rid] = None

    # If we will need to fall back to Ping.duration() more than 10 times
    # then disable duration display altogether:
    if num_misses > 10:
        for ping in pings:
            ping.duration = None

    return JsonResponse({"pings": [p.to_dict() for p in pings]})


@cors("GET")
@csrf_exempt
@authorize
def ping_body(request: ApiRequest, code: UUID, n: int) -> HttpResponse:
    check = get_object_or_404(Check, code=code)
    if check.project_id != request.project.id:
        return HttpResponseForbidden()

    profile = Profile.objects.get(user__project=request.project)
    threshold = check.n_pings - profile.ping_log_limit
    if n <= threshold:
        raise Http404()

    ping = get_object_or_404(Ping, owner=check, n=n)
    body = ping.get_body_bytes()
    if not body:
        raise Http404()

    response = HttpResponse(body, content_type="text/plain")
    return response


def flips(request: ApiRequest, check: Check) -> HttpResponse:
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
        threshold = now() - td(seconds=form.cleaned_data["seconds"])
        flips = flips.filter(created__gte=threshold)

    return JsonResponse({"flips": [flip.to_dict() for flip in flips]})


@cors("GET")
@csrf_exempt
@authorize_read
def flips_by_uuid(request: ApiRequest, code: UUID) -> HttpResponse:
    check = get_object_or_404(Check, code=code)
    return flips(request, check)


@cors("GET")
@csrf_exempt
@authorize_read
def flips_by_unique_key(request: ApiRequest, unique_key: str) -> HttpResponse:
    for check in request.project.check_set.all():
        if check.unique_key == unique_key:
            return flips(request, check)
    return HttpResponseNotFound()


@cors("GET")
@csrf_exempt
@authorize_read
def badges(request: ApiRequest) -> JsonResponse:
    tags = set(["*"])
    for check in request.project.check_set.all():
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


SHIELDS_COLORS = {"up": "success", "late": "important", "down": "critical"}


def _shields_response(label: str, status: str) -> JsonResponse:
    return JsonResponse(
        {
            "schemaVersion": 1,
            "label": label,
            "message": status,
            "color": SHIELDS_COLORS[status],
        }
    )


@never_cache
@cors("GET")
def badge(
    request: HttpRequest, badge_key: str, signature: str, tag: str, fmt: str
) -> HttpResponse:
    if fmt not in ("svg", "json", "shields"):
        return HttpResponseNotFound()

    with_late = True
    if len(signature) == 10 and signature.endswith("-2"):
        with_late = False

    if not check_signature(badge_key, tag, signature):
        return HttpResponseNotFound()

    q = Check.objects.filter(project__badge_key=badge_key)
    if tag == "*":
        label = settings.MASTER_BADGE_LABEL
    else:
        q = q.filter(tags__contains=tag)
        label = tag

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
        return _shields_response(label, status)

    if fmt == "json":
        return JsonResponse(
            {"status": status, "total": total, "grace": grace, "down": down}
        )

    svg = get_badge_svg(label, status)
    return HttpResponse(svg, content_type="image/svg+xml")


@never_cache
@cors("GET")
def check_badge(
    request: HttpRequest, states: int, badge_key: UUID, fmt: str
) -> HttpResponse:
    if fmt not in ("svg", "json", "shields"):
        return HttpResponseNotFound()

    check = get_object_or_404(Check, badge_key=badge_key)
    check_status = check.get_status()
    status = "up"
    if check_status == "down":
        status = "down"
    elif check_status == "grace" and states == 3:
        status = "late"

    if fmt == "shields":
        return _shields_response(check.name_then_code(), status)

    if fmt == "json":
        return JsonResponse(
            {
                "status": status,
                "total": 1,
                "grace": 1 if check_status == "grace" else 0,
                "down": 1 if check_status == "down" else 0,
            }
        )

    svg = get_badge_svg(check.name_then_code(), status)
    return HttpResponse(svg, content_type="image/svg+xml")


@csrf_exempt
@require_POST
def notification_status(request: HttpRequest, code: UUID) -> HttpResponse:
    """Handle notification delivery status callbacks."""

    try:
        cutoff = now() - td(hours=1)
        notification = Notification.objects.get(code=code, created__gt=cutoff)
    except Notification.DoesNotExist:
        # If the notification does not exist, or is more than a hour old,
        # return HTTP 200 so the other party doesn't retry over and over again:
        return HttpResponse()

    error, mark_disabled = None, False

    # Look for "error" and "mark_disabled" keys:
    if request.POST.get("error"):
        error = request.POST["error"][:200]
        mark_disabled = bool(request.POST.get("mark_disabled"))

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


def metrics(request: HttpRequest) -> HttpResponse:
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


def status(request: HttpRequest) -> HttpResponse:
    with connection.cursor() as c:
        c.execute("SELECT 1")
        c.fetchone()

    return HttpResponse("OK")


@csrf_exempt
def bounces(request: HttpRequest) -> HttpResponse:
    msg = message_from_bytes(request.body, policy=email.policy.SMTP)
    to_local = msg.get("To", "").split("@")[0]

    try:
        unsigned = unsign_bounce_id(to_local, max_age=3600 * 48)
    except BadSignature:
        # If the signature is invalid or expired return HTTP 200 so the other party
        # doesn't retry over and over again-
        return HttpResponse("OK (bad signature)")

    status, diagnostic = "", ""
    for part in msg.walk():
        if "Status" in part and "Action" in part:
            status = part["Status"]
            diagnostic = part.get("Diagnostic-Code", "")
            if diagnostic.lower().startswith("smtp; "):
                diagnostic = diagnostic[6:]
            break

    permanent = status.startswith("5.")
    transient = status.startswith("4.")
    if not permanent and not transient:
        return HttpResponse("OK (ignored)")

    if unsigned.startswith("n."):
        notification_code = unsigned[2:]
        try:
            cutoff = now() - td(hours=48)
            n = Notification.objects.get(code=notification_code, created__gt=cutoff)
        except Notification.DoesNotExist:
            return HttpResponse("OK (notification not found)")

        if diagnostic:
            error = f"Delivery failed ({diagnostic})"[:200]
        else:
            error = f"Delivery failed (SMTP status code: {status})"[:200]

        n.error = error
        n.save(update_fields=["error"])

        channel_q = Channel.objects.filter(id=n.channel_id)
        channel_q.update(last_error=error)

        if permanent:
            channel_q.update(disabled=True)

    if unsigned.startswith("r.") and permanent:
        username = unsigned[2:]

        try:
            profile = Profile.objects.get(user__username=username)
        except Profile.DoesNotExist:
            return HttpResponse("OK (user not found)")

        profile.reports = "off"
        profile.next_report_date = None
        profile.nag_period = td()
        profile.next_nag_date = None
        profile.save()

    return HttpResponse("OK")
