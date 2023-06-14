from __future__ import annotations

import email
import json
import os
import re
import sqlite3
import sys
import uuid
from collections import defaultdict
from datetime import timedelta as td
from secrets import token_urlsafe
from urllib.parse import urlencode, urlparse
from uuid import UUID

from cronsim import CronSim, CronSimError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db.models import Count, F
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import get_template, render_to_string
from django.urls import reverse
from django.utils.timezone import now
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from hc.accounts.models import Member, Project
from hc.api.models import (
    DEFAULT_GRACE,
    DEFAULT_TIMEOUT,
    MAX_DURATION,
    Channel,
    Check,
    Notification,
    Ping,
    TokenBucket,
)
from hc.api.transports import Signal, Telegram, TransportError
from hc.front import forms
from hc.front.decorators import require_setting
from hc.front.schemas import telegram_callback
from hc.front.templatetags.hc_extras import (
    down_title,
    num_down_title,
    site_hostname,
    sortchecks,
)
from hc.lib import curl, jsonschema
from hc.lib.badges import get_badge_url
from hc.lib.tz import all_timezones

if sys.version_info >= (3, 9):
    from zoneinfo import ZoneInfo
else:
    from backports.zoneinfo import ZoneInfo


VALID_SORT_VALUES = ("name", "-name", "last_ping", "-last_ping", "created")
STATUS_TEXT_TMPL = get_template("front/log_status_text.html")
LAST_PING_TMPL = get_template("front/last_ping_cell.html")
EVENTS_TMPL = get_template("front/details_events.html")
DOWNTIMES_TMPL = get_template("front/details_downtimes.html")


def _tags_statuses(checks):
    tags, down, grace, num_down = {}, {}, {}, 0
    for check in checks:
        status = check.get_status()

        if status == "down":
            num_down += 1
            for tag in check.tags_list():
                down[tag] = "down"
        elif status == "grace":
            for tag in check.tags_list():
                grace[tag] = "grace"
        else:
            for tag in check.tags_list():
                tags[tag] = "up"

    tags.update(grace)
    tags.update(down)
    return tags, num_down


def _get_check_for_user(
    request: HttpRequest, code: UUID, preload_owner_profile: bool = False
) -> tuple[Check, bool]:
    """Return specified check if current user has access to it.

    If `preload_owner_profile` is `True`, the returned check's
    project.owner.profile will be already loaded. This helps avoid extra SQL queries
    if the caller later looks up the project owner's check_limit or ping_log_limit.

    """

    assert request.user.is_authenticated

    q = Check.objects.select_related("project")
    if preload_owner_profile:
        q = q.select_related("project__owner__profile")

    check = get_object_or_404(q, code=code)
    if request.user.is_superuser:
        return check, True

    if request.user.id == check.project.owner_id:
        return check, True

    membership = get_object_or_404(Member, project=check.project, user=request.user)
    return check, membership.is_rw


def _get_rw_check_for_user(request: HttpRequest, code: UUID) -> Check:
    check, rw = _get_check_for_user(request, code)
    if not rw:
        raise PermissionDenied

    return check


def _get_channel_for_user(request: HttpRequest, code: UUID) -> tuple[Channel, bool]:
    """Return specified channel if current user has access to it."""

    assert request.user.is_authenticated

    channel = get_object_or_404(Channel.objects.select_related("project"), code=code)
    if request.user.is_superuser:
        return channel, True

    if request.user.id == channel.project.owner_id:
        return channel, True

    membership = get_object_or_404(Member, project=channel.project, user=request.user)
    return channel, membership.is_rw


def _get_rw_channel_for_user(request: HttpRequest, code: UUID) -> Channel:
    channel, rw = _get_channel_for_user(request, code)
    if not rw:
        raise PermissionDenied

    return channel


def _get_project_for_user(request: HttpRequest, code: UUID) -> tuple[Project, bool]:
    """Check access, return (project, rw) tuple."""

    project = get_object_or_404(Project, code=code)
    if request.user.is_superuser:
        return project, True

    if request.user.id == project.owner_id:
        return project, True

    membership = get_object_or_404(Member, project=project, user=request.user)

    return project, membership.is_rw


def _get_rw_project_for_user(request: HttpRequest, code: UUID) -> Project:
    """Check access, return (project, rw) tuple."""

    project, rw = _get_project_for_user(request, code)
    if not rw:
        raise PermissionDenied

    return project


def _refresh_last_active_date(profile):
    """Update last_active_date if it is more than a day old."""

    if profile.last_active_date is None or (now() - profile.last_active_date).days > 0:
        profile.last_active_date = now()
        profile.save()


def _get_referer_qs(request):
    parsed = urlparse(request.META.get("HTTP_REFERER", ""))
    if parsed.query:
        return "?" + parsed.query
    return ""


@login_required
def my_checks(request, code):
    _refresh_last_active_date(request.profile)
    project, rw = _get_project_for_user(request, code)

    if request.GET.get("sort") in VALID_SORT_VALUES:
        request.profile.sort = request.GET["sort"]
        request.profile.save()

    if request.GET.get("urls") in ("uuid", "slug") and rw:
        project.show_slugs = request.GET["urls"] == "slug"
        project.save()

    if request.session.get("last_project_id") != project.id:
        request.session["last_project_id"] = project.id

    q = Check.objects.filter(project=project)
    q = q.select_related("project")
    checks = list(q.prefetch_related("channel_set"))
    sortchecks(checks, request.profile.sort)

    tags_statuses, num_down = _tags_statuses(checks)
    pairs = list(tags_statuses.items())
    pairs.sort(key=lambda pair: pair[0].lower())

    channels = Channel.objects.filter(project=project)
    channels = list(channels.order_by("created"))

    hidden_checks = set()
    # Hide checks that don't match selected tags:
    selected_tags = set(request.GET.getlist("tag", []))
    if selected_tags:
        for check in checks:
            if not selected_tags.issubset(check.tags_list()):
                hidden_checks.add(check)

    # Hide checks that don't match the search string:
    search = request.GET.get("search", "")
    if search:
        for check in checks:
            search_key = "%s\n%s" % (check.name.lower(), check.code)
            if search not in search_key:
                hidden_checks.add(check)

    # Figure out which checks have ambiguous ping URLs
    seen, ambiguous = set(), set()
    if project.show_slugs:
        for check in checks:
            if check.slug and check.slug in seen:
                ambiguous.add(check.slug)
            else:
                seen.add(check.slug)

    # Do we need to show the "Last Duration" header?
    show_last_duration = False
    for check in checks:
        if check.clamped_last_duration():
            show_last_duration = True
            break

    ctx = {
        "page": "checks",
        "rw": rw,
        "checks": checks,
        "channels": channels,
        "num_down": num_down,
        "tags": pairs,
        "ping_endpoint": settings.PING_ENDPOINT,
        "timezones": all_timezones,
        "project": project,
        "num_available": project.num_checks_available(),
        "sort": request.profile.sort,
        "selected_tags": selected_tags,
        "search": search,
        "hidden_checks": hidden_checks,
        "ambiguous": ambiguous,
        "show_last_duration": show_last_duration,
    }

    return render(request, "front/my_checks.html", ctx)


@login_required
def status(request, code):
    project, rw = _get_project_for_user(request, code)
    checks = list(Check.objects.filter(project=project))

    details = []
    for check in checks:
        ctx = {"check": check}
        details.append(
            {
                "code": str(check.code),
                "status": check.get_status(),
                "last_ping": LAST_PING_TMPL.render(ctx).strip(),
                "started": check.last_start is not None,
            }
        )

    tags_statuses, num_down = _tags_statuses(checks)
    return JsonResponse(
        {"details": details, "tags": tags_statuses, "title": num_down_title(num_down)}
    )


@login_required
@require_POST
def switch_channel(request, code, channel_code):
    check = _get_rw_check_for_user(request, code)

    channel = get_object_or_404(Channel, code=channel_code)
    if channel.project_id != check.project_id:
        return HttpResponseBadRequest()

    if request.POST.get("state") == "on":
        channel.checks.add(check)
    else:
        channel.checks.remove(check)

    return HttpResponse()


def _get_project_summary(profile):
    statuses = defaultdict(lambda: {"status": "up", "started": False})
    q = profile.checks_from_all_projects()
    q = q.annotate(project_code=F("project__code"))
    for check in q:
        summary = statuses[check.project_code]
        if check.last_start:
            summary["started"] = True

        if summary["status"] != "down":
            status = check.get_status()
            if status == "down" or (status == "grace" and summary["status"] == "up"):
                summary["status"] = status

    return statuses


def index(request):
    if not request.user.is_authenticated:
        return redirect("hc-login")

    summary = _get_project_summary(request.profile)
    if "refresh" in request.GET:
        return JsonResponse({str(k): v for k, v in summary.items()})

    q = request.profile.projects()
    q = q.annotate(n_checks=Count("check", distinct=True))
    q = q.annotate(n_channels=Count("channel", distinct=True))
    q = q.annotate(owner_email=F("owner__email"))
    projects = list(q)
    for project in projects:
        project.overall_status = summary[project.code]["status"]
        project.any_started = summary[project.code]["started"]

    # The list returned by projects() is already sorted . Do an additional sorting pass
    # to move projects with overall_status=down to the front (without changing their
    # relative order)
    projects.sort(key=lambda p: p.overall_status != "down")

    ctx = {
        "page": "projects",
        "projects": projects,
        "last_project_id": request.session.get("last_project_id"),
    }

    return render(request, "front/projects.html", ctx)


@login_required
def projects_menu(request):
    projects = list(request.profile.projects())

    statuses = defaultdict(lambda: "up")
    for check in Check.objects.filter(project__in=projects):
        old_status = statuses[check.project_id]
        if old_status != "down":
            status = check.get_status()
            if status == "down" or (status == "grace" and old_status == "up"):
                statuses[check.project_id] = status

    for p in projects:
        p.overall_status = statuses[p.id]

    return render(request, "front/projects_menu.html", {"projects": projects})


def dashboard(request):
    return render(request, "front/dashboard.html", {})


def _replace_placeholders(doc, html):
    if doc.startswith("self_hosted"):
        return html

    limit = settings.PING_BODY_LIMIT or 100
    if limit % 1000 == 0:
        limit_fmt = f"{limit // 1000} kB"
    else:
        limit_fmt = f"{limit} bytes"

    replaces = {
        "{{ default_timeout }}": str(int(DEFAULT_TIMEOUT.total_seconds())),
        "{{ default_grace }}": str(int(DEFAULT_GRACE.total_seconds())),
        "SITE_NAME": settings.SITE_NAME,
        "SITE_ROOT": settings.SITE_ROOT,
        "SITE_HOSTNAME": site_hostname(),
        "SITE_SCHEME": urlparse(settings.SITE_ROOT).scheme,
        "PING_ENDPOINT": settings.PING_ENDPOINT,
        "PING_URL": settings.PING_ENDPOINT + "your-uuid-here",
        "PING_BODY_LIMIT_FORMATTED": limit_fmt,
        "PING_BODY_LIMIT": str(limit),
        "IMG_URL": os.path.join(settings.STATIC_URL, "img/docs"),
    }

    for placeholder, value in replaces.items():
        html = html.replace(placeholder, value)

    return html


def serve_doc(request, doc="introduction"):
    # Filenames in /templates/docs/ consist of lowercase letters and underscores,
    # -- make sure we don't accept anything else
    if not re.match(r"^[0-9a-z_]+$", doc):
        raise Http404("not found")

    path = settings.BASE_DIR / f"templates/docs/{doc}.html-fragment"
    if not path.exists():
        raise Http404("not found")

    with path.open("r", encoding="utf-8") as f:
        content = f.read()

    content = _replace_placeholders(doc, content)
    ctx = {
        "page": "docs",
        "section": doc,
        "content": content,
        "first_line": content.split("\n")[0],
    }

    return render(request, "front/docs_single.html", ctx)


@csrf_exempt
def docs_search(request):
    form = forms.SearchForm(request.GET)
    if not form.is_valid():
        ctx = {"results": []}
        return render(request, "front/docs_search.html", ctx)

    query = """
        SELECT slug, title, snippet(docs, 2, '<span>', '</span>', '&hellip;', 10)
        FROM docs
        WHERE docs MATCH ?
        ORDER BY bm25(docs, 2.0, 10.0, 1.0)
        LIMIT 8
    """

    q = form.cleaned_data["q"]
    con = sqlite3.connect(settings.BASE_DIR / "search.db")
    cur = con.cursor()
    res = cur.execute(query, (q,))

    ctx = {"results": res.fetchall()}
    return render(request, "front/docs_search.html", ctx)


def docs_cron(request):
    return render(request, "front/docs_cron.html", {"page": "docs-cron"})


@require_POST
@login_required
def add_check(request, code):
    project = _get_rw_project_for_user(request, code)
    if project.num_checks_available() <= 0:
        return HttpResponseBadRequest()

    form = forms.AddCheckForm(request.POST)
    if not form.is_valid():
        return HttpResponseBadRequest()

    check = Check(project=project)
    check.name = form.cleaned_data["name"]
    check.slug = form.cleaned_data["slug"]
    check.tags = form.cleaned_data["tags"]
    check.kind = form.cleaned_data["kind"]
    check.timeout = form.cleaned_data["timeout"]
    check.schedule = form.cleaned_data["schedule"]
    check.tz = form.cleaned_data["tz"]
    check.grace = form.cleaned_data["grace"]
    check.save()

    check.assign_all_channels()

    url = reverse("hc-checks", args=[project.code])
    url += _get_referer_qs(request)  # Preserve selected tags and search
    return redirect(url)


@require_POST
@login_required
def update_name(request, code):
    check = _get_rw_check_for_user(request, code)

    form = forms.NameTagsForm(request.POST)
    if form.is_valid():
        check.name = form.cleaned_data["name"]
        check.slug = form.cleaned_data["slug"]
        check.tags = form.cleaned_data["tags"]
        check.desc = form.cleaned_data["desc"]
        check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    url = reverse("hc-checks", args=[check.project.code])
    url += _get_referer_qs(request)  # Preserve selected tags and search
    return redirect(url)


@require_POST
@login_required
def filtering_rules(request, code):
    check = _get_rw_check_for_user(request, code)

    form = forms.FilteringRulesForm(request.POST)
    if form.is_valid():
        check.filter_subject = form.cleaned_data["filter_subject"]
        check.filter_body = form.cleaned_data["filter_body"]
        check.start_kw = form.cleaned_data["start_kw"]
        check.success_kw = form.cleaned_data["success_kw"]
        check.failure_kw = form.cleaned_data["failure_kw"]

        check.methods = form.cleaned_data["methods"]
        check.manual_resume = form.cleaned_data["manual_resume"]
        check.save()

    return redirect("hc-details", code)


@require_POST
@login_required
def update_timeout(request, code):
    check = _get_rw_check_for_user(request, code)

    kind = request.POST.get("kind")
    if kind == "simple":
        form = forms.TimeoutForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "simple"
        check.timeout = form.cleaned_data["timeout"]
        check.grace = form.cleaned_data["grace"]
    elif kind == "cron":
        form = forms.CronForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "cron"
        check.schedule = form.cleaned_data["schedule"]
        check.tz = form.cleaned_data["tz"]
        check.grace = td(minutes=form.cleaned_data["grace"])

    check.alert_after = check.going_down_after()
    if check.status == "up" and check.alert_after < now():
        # Checks can flip from "up" to "down" state as a result of changing check's
        # schedule.  We don't want to send notifications when changing schedule
        # interactively in the web UI. So we update the `alert_after` and `status`
        # fields, and create a Flip object here the same way as `sendalerts` would do,
        # but without sending an actual alert.
        #
        # We need to create the Flip object because otherwise the calculation
        # in Check.downtimes() will come out wrong (when this check later comes up,
        # we will have no record of when it went down).
        check.create_flip("down", mark_as_processed=True)

        check.alert_after = None
        check.status = "down"

    check.save()

    if "/details/" in request.META.get("HTTP_REFERER", ""):
        return redirect("hc-details", code)

    url = reverse("hc-checks", args=[check.project.code])
    url += _get_referer_qs(request)  # Preserve selected tags and search
    return redirect(url)


@require_POST
def cron_preview(request):
    schedule = request.POST.get("schedule", "")
    tz = request.POST.get("tz")
    ctx = {"tz": tz, "dates": []}

    if tz not in all_timezones:
        ctx["bad_tz"] = True
        return render(request, "front/cron_preview.html", ctx)

    now_local = now().astimezone(ZoneInfo(tz))
    try:
        it = CronSim(schedule, now_local)
        for i in range(0, 6):
            ctx["dates"].append(next(it))
        ctx["desc"] = it.explain()
    except (CronSimError, StopIteration):
        ctx["bad_schedule"] = True

    return render(request, "front/cron_preview.html", ctx)


def validate_schedule(request):
    schedule = request.GET.get("schedule", "")
    result = True
    try:
        # Does cronsim accept the schedule?
        it = CronSim(schedule, now())
        # Can it calculate the next datetime?
        next(it)
    except (CronSimError, StopIteration):
        result = False

    return JsonResponse({"result": result})


@login_required
def ping_details(request, code, n=None):
    check, rw = _get_check_for_user(request, code)
    q = Ping.objects.filter(owner=check)
    if n:
        q = q.filter(n=n)
    else:
        # When n is not specified, look up the most recent success or failure,
        # ignoring "start", "log", "ign" events
        q = q.exclude(kind__in=("start", "log", "ign"))

    try:
        ping = q.latest("created")
    except Ping.DoesNotExist:
        return render(request, "front/ping_details_not_found.html")

    body = ping.get_body()
    ctx = {
        "check": check,
        "ping": ping,
        "body": body,
        "plain": None,
        "html": None,
        "active": None,
    }

    if ping.scheme == "email":
        parsed = email.message_from_string(body, policy=email.policy.SMTP)
        ctx["subject"] = parsed.get("subject", "")

        # The "active" tab is set to show the value that's successfully parsed last. Per the current implementation,
        # this means that if both plain text and HTML content are present, the ping details dialog will initially
        # display the HTML content, otherwise - only one content type exists, and we default to that (either plain text
        # or HTML, at least one of them should exist in a valid email).
        #
        # NOTE: If both plain text and html have not been parsed successfully the "active" tab is not set at all, but
        # currently this is not an issue since in this case the "ping details" template does not render any tabs.

        plain_mime_part = parsed.get_body(("plain",))
        if plain_mime_part:
            ctx["plain"] = plain_mime_part.get_content()
            ctx["active"] = "plain"

        html_mime_part = parsed.get_body(("html",))
        if html_mime_part:
            ctx["html"] = html_mime_part.get_content()
            ctx["active"] = "html"

    return render(request, "front/ping_details.html", ctx)


@login_required
def ping_body(request, code, n):
    check, rw = _get_check_for_user(request, code)
    ping = get_object_or_404(Ping, owner=check, n=n)

    body = ping.get_body_bytes()
    if not body:
        raise Http404("not found")

    response = HttpResponse(body, content_type="application/octet-stream")
    filename = "%s-%s" % (check.code, ping.n)
    response["Content-Disposition"] = f'attachment; filename="{filename}.txt"'
    return response


@require_POST
@login_required
def pause(request, code):
    check = _get_rw_check_for_user(request, code)

    # Track the status change for correct downtime calculation in Check.downtimes()
    check.create_flip("paused", mark_as_processed=True)

    check.status = "paused"
    check.last_start = None
    check.alert_after = None
    check.save()

    # After pausing a check we must check if all checks are up,
    # and Profile.next_nag_date needs to be cleared out:
    check.project.update_next_nag_dates()

    # Don't redirect after an AJAX request:
    if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
        return HttpResponse()

    return redirect("hc-details", code)


@require_POST
@login_required
def resume(request, code):
    check = _get_rw_check_for_user(request, code)
    if check.status != "paused":
        return HttpResponseBadRequest()

    check.create_flip("new", mark_as_processed=True)

    check.status = "new"
    check.last_start = None
    check.last_ping = None
    check.alert_after = None
    check.save()

    return redirect("hc-details", code)


@require_POST
@login_required
def remove_check(request: HttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    project = check.project
    check.lock_and_delete()
    return redirect("hc-checks", project.code)


@require_POST
@login_required
def clear_events(request: HttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    check.status = "new"
    check.last_ping = None
    check.last_start = None
    check.last_duration = None
    check.has_confirmation_link = False
    check.alert_after = None
    check.save()

    check.ping_set.all().delete()
    check.notification_set.all().delete()
    check.flip_set.all().delete()

    return redirect("hc-details", code)


def _get_events(check, page_limit, start=None, end=None):
    pings = check.visible_pings.order_by("-id")
    if start and end:
        pings = pings.filter(created__gte=start, created__lte=end)

    pings = list(pings[:page_limit])

    # Optimization: the template will access Ping.duration, which would generate a
    # SQL query per displayed ping. Since we've already fetched a list of pings,
    # for some of them we can calculate durations more efficiently, without causing
    # additional SQL queries:
    starts, num_misses = {}, 0
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
                if starts[ping.rid]:
                    if ping.created - starts[ping.rid] < MAX_DURATION:
                        ping.duration = ping.created - starts[ping.rid]

            starts[ping.rid] = None

    # If we will need to fall back to Ping.duration() more than 10 times
    # then disable duration display altogether:
    if num_misses > 10:
        for ping in pings:
            ping.duration = None

    alerts = Notification.objects.select_related("channel")
    alerts = alerts.filter(owner=check, check_status="down")
    if start and end:
        alerts = alerts.filter(created__gte=start, created__lte=end)
    elif len(pings):
        cutoff = pings[-1].created
        alerts = alerts.filter(created__gt=cutoff)
    else:
        alerts = []

    events = pings + list(alerts)
    events.sort(key=lambda el: el.created, reverse=True)
    return events


@login_required
def log(request, code):
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    smax = now()
    smin = smax - td(hours=24)

    oldest_ping = check.visible_pings.order_by("n").first()
    if oldest_ping:
        smin = min(smin, oldest_ping.created)

    # Align slider steps to full hours
    smin = smin.replace(minute=0, second=0)

    form = forms.SeekForm(request.GET)
    if form.is_valid():
        start = form.cleaned_data["start"]
        end = form.cleaned_data["end"]
    else:
        start, end = smin, smax

    # Clamp the _get_events start argument to the date of the oldest visible ping
    get_events_start = start
    if oldest_ping and oldest_ping.created > get_events_start:
        get_events_start = oldest_ping.created

    total = check.visible_pings.filter(created__gte=start, created__lte=end).count()
    events = _get_events(check, 1000, start=get_events_start, end=end)
    ctx = {
        "page": "log",
        "project": check.project,
        "check": check,
        "min": smin,
        "max": smax,
        "start": start,
        "end": end,
        "events": events,
        "num_total": total,
    }

    return render(request, "front/log.html", ctx)


@login_required
def details(request, code):
    _refresh_last_active_date(request.profile)
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    if request.GET.get("urls") in ("uuid", "slug") and rw:
        check.project.show_slugs = request.GET["urls"] == "slug"
        check.project.save()

    channels = Channel.objects.filter(project=check.project)
    channels = list(channels.order_by("created"))

    all_tags = set()
    q = Check.objects.filter(project=check.project).exclude(tags="")
    for tags in q.values_list("tags", flat=True):
        all_tags.update(tags.split(" "))

    ctx = {
        "page": "details",
        "project": check.project,
        "check": check,
        "rw": rw,
        "channels": channels,
        "enabled_channels": list(check.channel_set.all()),
        "timezones": all_timezones,
        "downtimes": check.downtimes(3, request.profile.tz),
        "tz": request.profile.tz,
        "is_copied": "copied" in request.GET,
        "all_tags": " ".join(sorted(all_tags)),
    }

    return render(request, "front/details.html", ctx)


@login_required
def uncloak(request, unique_key):
    for check in request.profile.checks_from_all_projects().only("code"):
        if check.unique_key == unique_key:
            return redirect("hc-details", check.code)

    raise Http404("not found")


@login_required
def transfer(request: HttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    if request.method == "POST":
        form = forms.TransferForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        target_project = _get_rw_project_for_user(request, form.cleaned_data["project"])
        if target_project.owner_id != check.project.owner_id:
            if target_project.num_checks_available() <= 0:
                return HttpResponseBadRequest()

        check.project = target_project
        check.save()
        check.assign_all_channels()

        messages.success(request, "Check transferred successfully!")
        return redirect("hc-details", code)

    ctx = {"check": check}
    return render(request, "front/transfer_modal.html", ctx)


@require_POST
@login_required
def copy(request, code):
    check = _get_rw_check_for_user(request, code)

    if check.project.num_checks_available() <= 0:
        return HttpResponseBadRequest()

    new_name = check.name + " (copy)"
    # Make sure we don't exceed the 100 character db field limit:
    if len(new_name) > 100:
        new_name = check.name[:90] + "... (copy)"

    new_slug = check.slug + "-copy"
    if len(new_slug) > 100:
        new_slug = ""

    copied = Check(project=check.project)
    copied.name = new_name
    copied.slug = new_slug
    copied.desc, copied.tags = check.desc, check.tags

    copied.filter_subject = check.filter_subject
    copied.filter_body = check.filter_body
    copied.start_kw = check.start_kw
    copied.success_kw = check.success_kw
    copied.failure_kw = check.failure_kw

    copied.methods = check.methods
    copied.manual_resume = check.manual_resume

    copied.kind = check.kind
    copied.timeout, copied.grace = check.timeout, check.grace
    copied.schedule, copied.tz = check.schedule, check.tz
    copied.save()

    copied.channel_set.add(*check.channel_set.all())

    url = reverse("hc-details", args=[copied.code])
    return redirect(url + "?copied")


@login_required
def status_single(request, code):
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    status = check.get_status()
    events = _get_events(check, 20)
    updated = "1"
    if len(events):
        updated = str(events[0].created.timestamp())

    doc = {
        "status": status,
        "status_text": STATUS_TEXT_TMPL.render({"check": check, "rw": rw}),
        "title": down_title(check),
        "updated": updated,
        "started": check.last_start is not None,
    }

    if updated != request.GET.get("u"):
        doc["events"] = EVENTS_TMPL.render({"check": check, "events": events})
        downtimes = check.downtimes(3, request.profile.tz)
        doc["downtimes"] = DOWNTIMES_TMPL.render(
            {"downtimes": downtimes, "tz": request.profile.tz}
        )

    return JsonResponse(doc)


@login_required
def badges(request, code):
    project, rw = _get_project_for_user(request, code)

    tags = set()
    for check in Check.objects.filter(project=project):
        tags.update(check.tags_list())

    sorted_tags = sorted(tags, key=lambda s: s.lower())
    sorted_tags.append("*")  # For the "overall status" badge

    key = project.badge_key
    urls = []
    for tag in sorted_tags:
        urls.append(
            {
                "tag": tag,
                "svg": get_badge_url(key, tag),
                "svg3": get_badge_url(key, tag, with_late=True),
                "json": get_badge_url(key, tag, fmt="json"),
                "json3": get_badge_url(key, tag, fmt="json", with_late=True),
                "shields": get_badge_url(key, tag, fmt="shields"),
                "shields3": get_badge_url(key, tag, fmt="shields", with_late=True),
            }
        )

    ctx = {
        "have_tags": len(urls) > 1,
        "page": "badges",
        "project": project,
        "badges": urls,
    }

    return render(request, "front/badges.html", ctx)


@login_required
def channels(request, code):
    project, rw = _get_project_for_user(request, code)

    if request.method == "POST":
        if not rw:
            return HttpResponseForbidden()

        code = request.POST["channel"]
        try:
            channel = Channel.objects.get(code=code)
        except Channel.DoesNotExist:
            return HttpResponseBadRequest()
        if channel.project_id != project.id:
            return HttpResponseForbidden()

        new_checks = []
        for key in request.POST:
            if key.startswith("check-"):
                code = key[6:]
                try:
                    check = Check.objects.get(code=code)
                except Check.DoesNotExist:
                    return HttpResponseBadRequest()
                if check.project_id != project.id:
                    return HttpResponseForbidden()
                new_checks.append(check)

        channel.checks.set(new_checks)
        return redirect("hc-channels", project.code)

    channels = Channel.objects.filter(project=project)
    channels = channels.order_by("created")
    channels = channels.annotate(n_checks=Count("checks"))

    ctx = {
        "page": "channels",
        "rw": rw,
        "project": project,
        "profile": project.owner_profile,
        "channels": channels,
        "enable_apprise": settings.APPRISE_ENABLED is True,
        "enable_call": bool(settings.TWILIO_AUTH),
        "enable_discord": bool(settings.DISCORD_CLIENT_ID),
        "enable_linenotify": bool(settings.LINENOTIFY_CLIENT_ID),
        "enable_matrix": bool(settings.MATRIX_ACCESS_TOKEN),
        "enable_mattermost": settings.MATTERMOST_ENABLED is True,
        "enable_msteams": settings.MSTEAMS_ENABLED is True,
        "enable_opsgenie": settings.OPSGENIE_ENABLED is True,
        "enable_pagertree": settings.PAGERTREE_ENABLED is True,
        "enable_pd": settings.PD_ENABLED is True,
        "enable_prometheus": settings.PROMETHEUS_ENABLED is True,
        "enable_pushbullet": bool(settings.PUSHBULLET_CLIENT_ID),
        "enable_pushover": bool(settings.PUSHOVER_API_TOKEN),
        "enable_rocketchat": settings.ROCKETCHAT_ENABLED is True,
        "enable_shell": settings.SHELL_ENABLED is True,
        "enable_signal": bool(settings.SIGNAL_CLI_SOCKET),
        "enable_slack": settings.SLACK_ENABLED is True,
        "enable_slack_btn": bool(settings.SLACK_CLIENT_ID),
        "enable_sms": bool(settings.TWILIO_AUTH),
        "enable_spike": settings.SPIKE_ENABLED is True,
        "enable_telegram": bool(settings.TELEGRAM_TOKEN),
        "enable_trello": bool(settings.TRELLO_APP_KEY),
        "enable_victorops": settings.VICTOROPS_ENABLED is True,
        "enable_webhooks": settings.WEBHOOKS_ENABLED is True,
        "enable_whatsapp": settings.TWILIO_USE_WHATSAPP,
        "enable_zulip": settings.ZULIP_ENABLED is True,
        "use_payments": settings.USE_PAYMENTS,
    }

    return render(request, "front/channels.html", ctx)


@login_required
def channel_checks(request, code):
    channel = _get_rw_channel_for_user(request, code)

    assigned = set(channel.checks.values_list("code", flat=True).distinct())
    checks = Check.objects.filter(project=channel.project).order_by("created")

    ctx = {"checks": checks, "assigned": assigned, "channel": channel}

    return render(request, "front/channel_checks.html", ctx)


@require_POST
@login_required
def update_channel_name(request, code):
    channel = _get_rw_channel_for_user(request, code)

    form = forms.ChannelNameForm(request.POST)
    if form.is_valid():
        channel.name = form.cleaned_data["name"]
        channel.save()

    return redirect("hc-channels", channel.project.code)


def verify_email(request, code, token):
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() == token:
        channel.email_verified = True
        channel.save()
        return render(request, "front/verify_email_success.html")

    return render(request, "bad_link.html")


@csrf_exempt
def unsubscribe_email(request, code, signed_token):
    ctx = {}

    # Some email servers open links in emails to check for malicious content.
    # To work around this, on GET requests we serve a confirmation form.
    # If the signature is at least 5 minutes old, we also include JS code to
    # auto-submit the form.
    signer = signing.TimestampSigner(salt="alerts")

    # First, check the signature without looking at the timestamp:
    try:
        token = signer.unsign(signed_token)
    except signing.BadSignature:
        return render(request, "bad_link.html")

    # Then, check if timestamp is older than 5 minutes:
    try:
        signer.unsign(signed_token, max_age=300)
    except signing.SignatureExpired:
        ctx["autosubmit"] = True

    channel = get_object_or_404(Channel, code=code, kind="email")
    if channel.make_token() != token:
        return render(request, "bad_link.html")

    if request.method != "POST":
        return render(request, "accounts/unsubscribe_submit.html", ctx)

    channel.delete()
    return render(request, "front/unsubscribe_success.html")


@require_POST
@login_required
def send_test_notification(request: HttpRequest, code: UUID) -> HttpResponse:
    channel, rw = _get_channel_for_user(request, code)

    dummy = Check(name="TEST", status="down", project=channel.project)
    dummy.last_ping = now() - td(days=1)
    dummy.n_pings = 42

    # Delete all older test notifications for this channel
    Notification.objects.filter(channel=channel, owner=None).delete()

    # Send the test notification
    error = channel.notify(dummy, is_test=True)

    if error == "no-op":
        # This channel may be configured to send "up" notifications only.
        dummy.status = "up"
        error = channel.notify(dummy, is_test=True)

    if error:
        messages.warning(request, "Could not send a test notification. %s." % error)
    else:
        messages.success(request, "Test notification sent!")

    return redirect("hc-channels", channel.project.code)


@require_POST
@login_required
def remove_channel(request: HttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)
    project = channel.project
    channel.delete()

    return redirect("hc-channels", project.code)


def email_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    # Convince mypy we have User instead of AnonymousUser:
    assert isinstance(request.user, User)

    adding = channel._state.adding
    if request.method == "POST":
        form = forms.EmailForm(request.POST)
        if form.is_valid():
            if channel.disabled or form.cleaned_data["value"] != channel.email_value:
                channel.disabled = False

                if not settings.EMAIL_USE_VERIFICATION:
                    # In self-hosted setting, administator can set
                    # EMAIL_USE_VERIFICATION=False to disable email verification
                    channel.email_verified = True
                elif form.cleaned_data["value"] == request.user.email:
                    # If the user is adding *their own* address
                    # we skip the verification step
                    channel.email_verified = True
                else:
                    channel.email_verified = False

            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()

            if not channel.email_verified:
                channel.send_verify_link()

            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.EmailForm()
    else:
        form = forms.EmailForm(
            {
                "value": channel.email_value,
                "up": channel.email_notify_up,
                "down": channel.email_notify_down,
            }
        )

    ctx = {
        "page": "channels",
        "project": channel.project,
        "use_verification": settings.EMAIL_USE_VERIFICATION,
        "form": form,
        "is_new": adding,
    }
    return render(request, "integrations/email_form.html", ctx)


@login_required
def add_email(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="email")
    return email_form(request, channel)


@login_required
def edit_channel(request: HttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)
    if channel.kind == "email":
        return email_form(request, channel)
    if channel.kind == "webhook":
        return webhook_form(request, channel)
    if channel.kind == "sms":
        return sms_form(request, channel)
    if channel.kind == "signal":
        return signal_form(request, channel)
    if channel.kind == "whatsapp":
        return whatsapp_form(request, channel)
    if channel.kind == "ntfy":
        return ntfy_form(request, channel)

    return HttpResponseBadRequest()


@require_setting("WEBHOOKS_ENABLED")
def webhook_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.WebhookForm(request.POST)
        if form.is_valid():
            channel.name = form.cleaned_data["name"]
            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()

            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.WebhookForm()
    else:

        def flatten(d):
            return "\n".join("%s: %s" % pair for pair in d.items())

        doc = json.loads(channel.value)
        doc["headers_down"] = flatten(doc["headers_down"])
        doc["headers_up"] = flatten(doc["headers_up"])
        doc["name"] = channel.name
        form = forms.WebhookForm(doc)

    ctx = {
        "page": "channels",
        "project": channel.project,
        "form": form,
        "is_new": adding,
    }
    return render(request, "integrations/webhook_form.html", ctx)


@require_setting("WEBHOOKS_ENABLED")
@login_required
def add_webhook(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="webhook")
    return webhook_form(request, channel)


@require_setting("SHELL_ENABLED")
@login_required
def add_shell(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.AddShellForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="shell")
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddShellForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
    }
    return render(request, "integrations/add_shell.html", ctx)


@require_setting("PD_ENABLED")
@login_required
def add_pd(request, code):
    project = _get_rw_project_for_user(request, code)

    # Simple Install Flow
    if settings.PD_APP_ID:
        state = token_urlsafe()

        redirect_url = settings.SITE_ROOT + reverse("hc-add-pd-complete")
        redirect_url += "?" + urlencode({"state": state})

        install_url = "https://app.pagerduty.com/install/integration?" + urlencode(
            {"app_id": settings.PD_APP_ID, "redirect_url": redirect_url, "version": "2"}
        )

        ctx = {"page": "channels", "project": project, "install_url": install_url}
        request.session["pagerduty"] = (state, str(project.code))
        return render(request, "integrations/add_pd_simple.html", ctx)

    if request.method == "POST":
        form = forms.AddPdForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="pd")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddPdForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_pd.html", ctx)


@require_setting("PD_ENABLED")
@require_setting("PD_APP_ID")
@login_required
def add_pd_complete(request):
    if "pagerduty" not in request.session:
        return HttpResponseBadRequest()

    state, code_str = request.session.pop("pagerduty")
    code = UUID(code_str)
    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    project = _get_rw_project_for_user(request, code)

    doc = json.loads(request.GET["config"])
    for item in doc["integration_keys"]:
        channel = Channel(kind="pd", project=project)
        channel.name = item["name"]
        channel.value = json.dumps(
            {"service_key": item["integration_key"], "account": doc["account"]["name"]}
        )
        channel.save()
        channel.assign_all_checks()

    messages.success(request, "The PagerDuty integration has been added!")
    return redirect("hc-channels", project.code)


@require_setting("PD_ENABLED")
@require_setting("PD_APP_ID")
def pd_help(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_pd_simple.html", ctx)


@require_setting("PAGERTREE_ENABLED")
@login_required
def add_pagertree(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="pagertree")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_pagertree.html", ctx)


@require_setting("SLACK_ENABLED")
@login_required
def add_slack(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="slack")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {
        "page": "channels",
        "form": form,
    }

    return render(request, "integrations/add_slack.html", ctx)


@require_setting("SLACK_ENABLED")
@require_setting("SLACK_CLIENT_ID")
def slack_help(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_slack_btn.html", ctx)


@require_setting("SLACK_ENABLED")
@require_setting("SLACK_CLIENT_ID")
@login_required
def add_slack_btn(request, code):
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = "https://slack.com/oauth/v2/authorize?" + urlencode(
        {
            "scope": "incoming-webhook",
            "client_id": settings.SLACK_CLIENT_ID,
            "state": state,
        }
    )

    ctx = {
        "project": project,
        "page": "channels",
        "authorize_url": authorize_url,
    }

    request.session["add_slack"] = (state, str(project.code))
    return render(request, "integrations/add_slack_btn.html", ctx)


@require_setting("SLACK_ENABLED")
@require_setting("SLACK_CLIENT_ID")
@login_required
def add_slack_complete(request: HttpRequest) -> HttpResponse:
    if "add_slack" not in request.session:
        return HttpResponseForbidden()

    state, code_str = request.session.pop("add_slack")
    code = UUID(code_str)
    project = _get_rw_project_for_user(request, code)
    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Slack setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    data = {
        "client_id": settings.SLACK_CLIENT_ID,
        "client_secret": settings.SLACK_CLIENT_SECRET,
        "code": request.GET.get("code"),
    }
    result = curl.post("https://slack.com/api/oauth.v2.access", data)

    doc = result.json()
    if doc.get("ok"):
        channel = Channel(kind="slack", project=project)
        channel.value = result.text
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The Slack integration has been added!")
    else:
        s = doc.get("error")
        messages.warning(request, "Error message from slack: %s" % s)

    return redirect("hc-channels", project.code)


@require_setting("MATTERMOST_ENABLED")
def mattermost_help(request):
    return render(request, "integrations/add_mattermost.html")


@require_setting("MATTERMOST_ENABLED")
@login_required
def add_mattermost(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="mattermost")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "form": form, "project": project}
    return render(request, "integrations/add_mattermost.html", ctx)


@require_setting("ROCKETCHAT_ENABLED")
def rocketchat_help(request):
    return render(request, "integrations/add_rocketchat.html")


@require_setting("ROCKETCHAT_ENABLED")
@login_required
def add_rocketchat(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="rocketchat")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "form": form, "project": project}
    return render(request, "integrations/add_rocketchat.html", ctx)


@require_setting("PUSHBULLET_CLIENT_ID")
@login_required
def add_pushbullet(request, code):
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = "https://www.pushbullet.com/authorize?" + urlencode(
        {
            "client_id": settings.PUSHBULLET_CLIENT_ID,
            "redirect_uri": settings.SITE_ROOT + reverse(add_pushbullet_complete),
            "response_type": "code",
            "state": state,
        }
    )

    ctx = {
        "page": "channels",
        "project": project,
        "authorize_url": authorize_url,
    }

    request.session["add_pushbullet"] = (state, str(project.code))
    return render(request, "integrations/add_pushbullet.html", ctx)


@require_setting("PUSHBULLET_CLIENT_ID")
@login_required
def add_pushbullet_complete(request):
    if "add_pushbullet" not in request.session:
        return HttpResponseForbidden()

    state, code_str = request.session.pop("add_pushbullet")
    code = UUID(code_str)
    project = _get_rw_project_for_user(request, code)

    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Pushbullet setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    data = {
        "client_id": settings.PUSHBULLET_CLIENT_ID,
        "client_secret": settings.PUSHBULLET_CLIENT_SECRET,
        "code": request.GET.get("code"),
        "grant_type": "authorization_code",
    }
    result = curl.post("https://api.pushbullet.com/oauth2/token", data)

    doc = result.json()
    if "access_token" in doc:
        channel = Channel(kind="pushbullet", project=project)
        channel.value = doc["access_token"]
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The Pushbullet integration has been added!")
    else:
        messages.warning(request, "Something went wrong")

    return redirect("hc-channels", project.code)


@require_setting("DISCORD_CLIENT_ID")
@login_required
def add_discord(request, code):
    project = _get_rw_project_for_user(request, code)
    state = token_urlsafe()
    auth_url = "https://discordapp.com/api/oauth2/authorize?" + urlencode(
        {
            "client_id": settings.DISCORD_CLIENT_ID,
            "scope": "webhook.incoming",
            "redirect_uri": settings.SITE_ROOT + reverse(add_discord_complete),
            "response_type": "code",
            "state": state,
        }
    )

    ctx = {"page": "channels", "project": project, "authorize_url": auth_url}

    request.session["add_discord"] = (state, str(project.code))
    return render(request, "integrations/add_discord.html", ctx)


@require_setting("DISCORD_CLIENT_ID")
@login_required
def add_discord_complete(request):
    if "add_discord" not in request.session:
        return HttpResponseForbidden()

    state, code_str = request.session.pop("add_discord")
    code = UUID(code_str)
    project = _get_rw_project_for_user(request, code)

    if request.GET.get("error") == "access_denied":
        messages.warning(request, "Discord setup was cancelled.")
        return redirect("hc-channels", project.code)

    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    data = {
        "client_id": settings.DISCORD_CLIENT_ID,
        "client_secret": settings.DISCORD_CLIENT_SECRET,
        "code": request.GET.get("code"),
        "grant_type": "authorization_code",
        "redirect_uri": settings.SITE_ROOT + reverse(add_discord_complete),
    }
    result = curl.post("https://discordapp.com/api/oauth2/token", data)

    doc = result.json()
    if "access_token" in doc:
        channel = Channel(kind="discord", project=project)
        channel.value = result.text
        channel.save()
        channel.assign_all_checks()
        messages.success(request, "The Discord integration has been added!")
    else:
        messages.warning(request, "Something went wrong.")

    return redirect("hc-channels", project.code)


@require_setting("PUSHOVER_API_TOKEN")
def pushover_help(request):
    ctx = {"page": "channels"}
    return render(request, "integrations/add_pushover_help.html", ctx)


@require_setting("PUSHOVER_API_TOKEN")
@login_required
def add_pushover(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        state = token_urlsafe()

        failure_url = settings.SITE_ROOT + reverse("hc-channels", args=[project.code])
        success_url = (
            settings.SITE_ROOT
            + reverse("hc-add-pushover", args=[project.code])
            + "?"
            + urlencode(
                {
                    "state": state,
                    "prio": request.POST.get("po_priority", "0"),
                    "prio_up": request.POST.get("po_priority_up", "0"),
                }
            )
        )
        subscription_url = (
            settings.PUSHOVER_SUBSCRIPTION_URL
            + "?"
            + urlencode({"success": success_url, "failure": failure_url})
        )

        request.session["pushover"] = state
        return redirect(subscription_url)

    # Handle successful subscriptions
    if "pushover_user_key" in request.GET:
        if "pushover" not in request.session:
            return HttpResponseForbidden()

        state = request.session.pop("pushover")
        if request.GET.get("state") != state:
            return HttpResponseForbidden()

        if request.GET.get("pushover_unsubscribed") == "1":
            # Unsubscription: delete all Pushover channels for this project
            Channel.objects.filter(project=project, kind="po").delete()
            return redirect("hc-channels", project.code)

        form = forms.AddPushoverForm(request.GET)
        if not form.is_valid():
            return HttpResponseBadRequest()

        channel = Channel(project=project, kind="po")
        channel.value = form.get_value()
        channel.save()
        channel.assign_all_checks()

        messages.success(request, "The Pushover integration has been added!")
        return redirect("hc-channels", project.code)

    # Show Integration Settings form
    ctx = {
        "page": "channels",
        "project": project,
        "po_retry_delay": td(seconds=settings.PUSHOVER_EMERGENCY_RETRY_DELAY),
        "po_expiration": td(seconds=settings.PUSHOVER_EMERGENCY_EXPIRATION),
    }
    return render(request, "integrations/add_pushover.html", ctx)


@require_setting("OPSGENIE_ENABLED")
@login_required
def add_opsgenie(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddOpsgenieForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="opsgenie")
            v = {"region": form.cleaned_data["region"], "key": form.cleaned_data["key"]}
            channel.value = json.dumps(v)
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddOpsgenieForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_opsgenie.html", ctx)


@require_setting("VICTOROPS_ENABLED")
@login_required
def add_victorops(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="victorops")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_victorops.html", ctx)


@require_setting("ZULIP_ENABLED")
@login_required
def add_zulip(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddZulipForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="zulip")
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddZulipForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_zulip.html", ctx)


@csrf_exempt
@require_POST
def telegram_bot(request):
    try:
        doc = json.loads(request.body.decode())
        if "channel_post" in doc:
            # Telegram's "channel_post" key uses the same structure as "message".
            # To keep the JSON schema and the view logic simple, if the payload
            # contains "channel_post", copy it to "message", and proceed as usual.
            doc["message"] = doc["channel_post"]

        jsonschema.validate(doc, telegram_callback)
    except ValueError:
        return HttpResponseBadRequest()
    except jsonschema.ValidationError:
        # We don't recognize the message format, but don't want Telegram
        # retrying this over and over again, so respond with 200 OK
        return HttpResponse()

    if "/start" not in doc["message"]["text"]:
        return HttpResponse()

    chat = doc["message"]["chat"]
    name = max(chat.get("title", ""), chat.get("username", ""))

    invite = render_to_string(
        "integrations/telegram_invite.html",
        {"qs": signing.dumps((chat["id"], chat["type"], name))},
    )

    try:
        Telegram.send(chat["id"], invite)
    except TransportError:
        # Swallow the error and return HTTP 200 OK, otherwise Telegram will
        # hit the webhook again and again.
        pass

    return HttpResponse()


@require_setting("TELEGRAM_TOKEN")
def telegram_help(request):
    ctx = {
        "page": "channels",
        "bot_name": settings.TELEGRAM_BOT_NAME,
    }

    return render(request, "integrations/add_telegram.html", ctx)


@require_setting("TELEGRAM_TOKEN")
@login_required
def add_telegram(request):
    chat_id, chat_type, chat_name = None, None, None
    if qs := request.META["QUERY_STRING"]:
        try:
            chat_id, chat_type, chat_name = signing.loads(qs, max_age=600)
        except signing.BadSignature:
            return render(request, "bad_link.html")

    if request.method == "POST":
        form = forms.AddTelegramForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        project = _get_rw_project_for_user(request, form.cleaned_data["project"])
        channel = Channel(project=project, kind="telegram")
        channel.value = json.dumps(
            {"id": chat_id, "type": chat_type, "name": chat_name}
        )
        channel.save()

        channel.assign_all_checks()
        messages.success(request, "The Telegram integration has been added!")
        return redirect("hc-channels", project.code)

    ctx = {
        "page": "channels",
        "projects": request.profile.projects(),
        "chat_id": chat_id,
        "chat_type": chat_type,
        "chat_name": chat_name,
        "bot_name": settings.TELEGRAM_BOT_NAME,
    }

    return render(request, "integrations/add_telegram.html", ctx)


@require_setting("TWILIO_AUTH")
def sms_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.PhoneUpDownForm(request.POST)
        if form.is_valid():
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_json()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.PhoneUpDownForm(initial={"up": False})
    else:
        form = forms.PhoneUpDownForm(
            {
                "label": channel.name,
                "phone": channel.phone_number,
                "up": channel.sms_notify_up,
                "down": channel.sms_notify_down,
            }
        )

    ctx = {
        "page": "channels",
        "project": channel.project,
        "form": form,
        "profile": channel.project.owner_profile,
        "is_new": adding,
    }
    return render(request, "integrations/sms_form.html", ctx)


@require_setting("TWILIO_AUTH")
@login_required
def add_sms(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="sms")
    return sms_form(request, channel)


@require_setting("TWILIO_AUTH")
@login_required
def add_call(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.PhoneNumberForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="call")
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_json()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.PhoneNumberForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
        "profile": project.owner_profile,
    }
    return render(request, "integrations/add_call.html", ctx)


@require_setting("TWILIO_USE_WHATSAPP")
def whatsapp_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.PhoneUpDownForm(request.POST)
        if form.is_valid():
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_json()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.PhoneUpDownForm()
    else:
        form = forms.PhoneUpDownForm(
            {
                "label": channel.name,
                "phone": channel.phone_number,
                "up": channel.whatsapp_notify_up,
                "down": channel.whatsapp_notify_down,
            }
        )

    ctx = {
        "page": "channels",
        "project": channel.project,
        "form": form,
        "profile": channel.project.owner_profile,
        "is_new": adding,
    }
    return render(request, "integrations/whatsapp_form.html", ctx)


@require_setting("TWILIO_USE_WHATSAPP")
@login_required
def add_whatsapp(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="whatsapp")
    return whatsapp_form(request, channel)


@require_setting("SIGNAL_CLI_SOCKET")
def signal_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.PhoneUpDownForm(request.POST)
        if form.is_valid():
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_json()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.PhoneUpDownForm()
    else:
        form = forms.PhoneUpDownForm(
            {
                "label": channel.name,
                "phone": channel.phone_number,
                "up": channel.signal_notify_up,
                "down": channel.signal_notify_down,
            }
        )

    ctx = {
        "page": "channels",
        "project": channel.project,
        "form": form,
        "is_new": adding,
    }
    return render(request, "integrations/signal_form.html", ctx)


@require_setting("SIGNAL_CLI_SOCKET")
@login_required
def add_signal(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="signal")
    return signal_form(request, channel)


@require_setting("TRELLO_APP_KEY")
@login_required
def add_trello(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.AddTrelloForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        channel = Channel(project=project, kind="trello")
        channel.value = form.get_value()
        channel.save()

        channel.assign_all_checks()
        return redirect("hc-channels", project.code)

    return_url = settings.SITE_ROOT + reverse("hc-add-trello", args=[project.code])
    authorize_url = "https://trello.com/1/authorize?" + urlencode(
        {
            "expiration": "never",
            "name": settings.SITE_NAME,
            "scope": "read,write",
            "response_type": "token",
            "key": settings.TRELLO_APP_KEY,
            "return_url": return_url,
        }
    )

    ctx = {
        "page": "channels",
        "project": project,
        "authorize_url": authorize_url,
    }

    return render(request, "integrations/add_trello.html", ctx)


@require_setting("MATRIX_ACCESS_TOKEN")
@login_required
def add_matrix(request, code):
    project = _get_rw_project_for_user(request, code)
    if request.method == "POST":
        form = forms.AddMatrixForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="matrix")
            channel.value = form.cleaned_data["room_id"]

            # If user supplied room alias instead of ID, use it as channel name
            alias = form.cleaned_data["alias"]
            if not alias.startswith("!"):
                channel.name = alias

            channel.save()

            channel.assign_all_checks()
            messages.success(request, "The Matrix integration has been added!")
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddMatrixForm()

    ctx = {
        "page": "channels",
        "project": project,
        "form": form,
        "matrix_user_id": settings.MATRIX_USER_ID,
    }
    return render(request, "integrations/add_matrix.html", ctx)


@require_setting("APPRISE_ENABLED")
@login_required
def add_apprise(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddAppriseForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="apprise")
            channel.value = form.cleaned_data["url"]
            channel.save()

            channel.assign_all_checks()
            messages.success(request, "The Apprise integration has been added!")
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddAppriseForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_apprise.html", ctx)


@require_setting("TRELLO_APP_KEY")
@login_required
@require_POST
def trello_settings(request):
    token = request.POST.get("token")

    url = "https://api.trello.com/1/members/me/boards"
    params = {
        "key": settings.TRELLO_APP_KEY,
        "token": token,
        "filter": "open",
        "fields": "id,name",
        "lists": "open",
        "list_fields": "id,name",
    }

    boards = curl.get(url, params=params).json()
    num_lists = sum(len(board["lists"]) for board in boards)

    ctx = {"token": token, "boards": boards, "num_lists": num_lists}
    return render(request, "integrations/trello_settings.html", ctx)


@require_setting("MSTEAMS_ENABLED")
@login_required
def add_msteams(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="msteams")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_msteams.html", ctx)


@require_setting("PROMETHEUS_ENABLED")
@login_required
def add_prometheus(request, code):
    project, rw = _get_project_for_user(request, code)
    ctx = {
        "page": "channels",
        "project": project,
        "site_scheme": urlparse(settings.SITE_ROOT).scheme,
    }
    return render(request, "integrations/add_prometheus.html", ctx)


@require_setting("PROMETHEUS_ENABLED")
def metrics(request, code, key):
    if len(key) != 32:
        return HttpResponseBadRequest()

    q = Project.objects.filter(code=code, api_key_readonly=key)
    try:
        project = q.get()
    except Project.DoesNotExist:
        return HttpResponseForbidden()

    checks = Check.objects.filter(project_id=project.id).order_by("id")

    def esc(s):
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def output(checks):
        yield "# HELP hc_check_up Whether the check is currently up (1 for yes, 0 for no).\n"
        yield "# TYPE hc_check_up gauge\n"

        TMPL = """hc_check_up{name="%s", tags="%s", unique_key="%s"} %d\n"""
        for check in checks:
            value = 0 if check.get_status() == "down" else 1
            yield TMPL % (esc(check.name), esc(check.tags), check.unique_key, value)

        yield "\n"
        yield "# HELP hc_check_started Whether the check is currently started (1 for yes, 0 for no).\n"
        yield "# TYPE hc_check_started gauge\n"
        TMPL = """hc_check_started{name="%s", tags="%s", unique_key="%s"} %d\n"""
        for check in checks:
            value = 1 if check.last_start is not None else 0
            yield TMPL % (esc(check.name), esc(check.tags), check.unique_key, value)

        tags_statuses, num_down = _tags_statuses(checks)
        yield "\n"
        yield "# HELP hc_tag_up Whether all checks with this tag are up (1 for yes, 0 for no).\n"
        yield "# TYPE hc_tag_up gauge\n"
        TMPL = """hc_tag_up{tag="%s"} %d\n"""
        for tag in sorted(tags_statuses):
            value = 0 if tags_statuses[tag] == "down" else 1
            yield TMPL % (esc(tag), value)

        yield "\n"
        yield "# HELP hc_checks_total The total number of checks.\n"
        yield "# TYPE hc_checks_total gauge\n"
        yield "hc_checks_total %d\n" % len(checks)
        yield "\n"

        yield "# HELP hc_checks_down_total The number of checks currently down.\n"
        yield "# TYPE hc_checks_down_total gauge\n"
        yield "hc_checks_down_total %d\n" % num_down

    return HttpResponse(output(checks), content_type="text/plain")


@require_setting("SPIKE_ENABLED")
@login_required
def add_spike(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddUrlForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="spike")
            channel.value = form.cleaned_data["value"]
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddUrlForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_spike.html", ctx)


@require_setting("LINENOTIFY_CLIENT_ID")
@login_required
def add_linenotify(request, code):
    project = _get_rw_project_for_user(request, code)

    state = token_urlsafe()
    authorize_url = " https://notify-bot.line.me/oauth/authorize?" + urlencode(
        {
            "client_id": settings.LINENOTIFY_CLIENT_ID,
            "redirect_uri": settings.SITE_ROOT + reverse(add_linenotify_complete),
            "response_type": "code",
            "state": state,
            "scope": "notify",
        }
    )

    ctx = {
        "page": "channels",
        "project": project,
        "authorize_url": authorize_url,
    }

    request.session["add_linenotify"] = (state, str(project.code))
    return render(request, "integrations/add_linenotify.html", ctx)


@require_setting("LINENOTIFY_CLIENT_ID")
@login_required
def add_linenotify_complete(request):
    if "add_linenotify" not in request.session:
        return HttpResponseForbidden()

    state, code_str = request.session.pop("add_linenotify")
    code = UUID(code_str)
    if request.GET.get("state") != state:
        return HttpResponseForbidden()

    project = _get_rw_project_for_user(request, code)
    if request.GET.get("error") == "access_denied":
        messages.warning(request, "LINE Notify setup was cancelled.")
        return redirect("hc-channels", project.code)

    # Exchange code for access token
    data = {
        "grant_type": "authorization_code",
        "code": request.GET.get("code"),
        "redirect_uri": settings.SITE_ROOT + reverse(add_linenotify_complete),
        "client_id": settings.LINENOTIFY_CLIENT_ID,
        "client_secret": settings.LINENOTIFY_CLIENT_SECRET,
    }
    result = curl.post("https://notify-bot.line.me/oauth/token", data)

    doc = result.json()
    if doc.get("status") != 200:
        messages.warning(request, "Something went wrong.")
        return redirect("hc-channels", project.code)

    # Fetch notification target's name, will use it as channel name:
    token = doc["access_token"]
    result = curl.get(
        "https://notify-api.line.me/api/status",
        headers={"Authorization": "Bearer %s" % token},
    )
    doc = result.json()

    channel = Channel(kind="linenotify", project=project)
    channel.name = doc.get("target")
    channel.value = token
    channel.save()
    channel.assign_all_checks()
    messages.success(request, "The LINE Notify integration has been added!")

    return redirect("hc-channels", project.code)


@login_required
def add_gotify(request, code):
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        form = forms.AddGotifyForm(request.POST)
        if form.is_valid():
            channel = Channel(project=project, kind="gotify")
            channel.value = form.get_value()
            channel.save()

            channel.assign_all_checks()
            return redirect("hc-channels", project.code)
    else:
        form = forms.AddGotifyForm()

    ctx = {"page": "channels", "project": project, "form": form}
    return render(request, "integrations/add_gotify.html", ctx)


def ntfy_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.NtfyForm(request.POST)
        if form.is_valid():
            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.NtfyForm()
    else:
        form = forms.NtfyForm(
            {
                "topic": channel.ntfy_topic,
                "url": channel.ntfy_url,
                "priority": channel.ntfy_priority,
                "priority_up": channel.ntfy_priority_up,
            }
        )

    ctx = {"page": "channels", "project": channel.project, "form": form}
    return render(request, "integrations/ntfy_form.html", ctx)


@login_required
def add_ntfy(request: HttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="ntfy")
    return ntfy_form(request, channel)


@require_setting("SIGNAL_CLI_SOCKET")
@login_required
def signal_captcha(request: HttpRequest) -> HttpResponse:
    if not request.user.is_superuser:
        return HttpResponseForbidden()

    ctx = {"challenge": request.GET.get("challenge", "")}
    if request.method == "POST":
        challenge = request.POST.get("challenge", "")
        captcha = request.POST.get("captcha", "")
        if captcha.startswith("signalcaptcha://"):
            captcha = captcha[16:]

        payload = {
            "jsonrpc": "2.0",
            "method": "submitRateLimitChallenge",
            "params": {"challenge": str(challenge), "captcha": captcha},
            "id": str(uuid.uuid4()),
        }

        payload_bytes = (json.dumps(payload) + "\n").encode()
        for reply_bytes in Signal(None)._read_replies(payload_bytes):
            try:
                reply = json.loads(reply_bytes.decode())
            except ValueError:
                ctx["result"] = "submitRateLimitChallenge failed"
                break

            if reply.get("id") == payload["id"]:
                ctx["result"] = reply_bytes.decode()
                break

    return render(request, "front/signal_captcha.html", ctx)


@require_setting("SIGNAL_CLI_SOCKET")
@login_required
@require_POST
def verify_signal_number(request: HttpRequest) -> HttpResponse:
    def render_result(result: str | None) -> HttpResponse:
        return render(request, "integrations/signal_result.html", {"result": result})

    # Enforce per-account rate limit (50 verifications per day)
    if not TokenBucket.authorize_signal_verification(request.user):
        return render_result("Verification rate limit exceeded")

    form = forms.PhoneNumberForm(request.POST)
    if not form.is_valid():
        return render_result("Invalid phone number")

    phone = form.cleaned_data["phone"]
    # Enforce per-recipient rate limit (6 messages per minute)
    if not TokenBucket.authorize_signal(phone):
        return render_result("Verification rate limit exceeded")

    try:
        Signal(None).send(phone, f"Test message from {settings.SITE_NAME}")
    except TransportError as e:
        return render_result(e.message)

    # Success!
    return render_result(None)


# Forks: add custom views after this line
