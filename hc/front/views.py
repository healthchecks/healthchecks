from __future__ import annotations

import email
import json
import logging
import os
import re
import sqlite3
import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime
from datetime import timedelta as td
from email.message import EmailMessage
from secrets import token_urlsafe
from typing import Literal, TypedDict, cast
from urllib.parse import urlencode, urlparse
from uuid import UUID
from zoneinfo import ZoneInfo

from cronsim import CronSim, CronSimError
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core import signing
from django.core.exceptions import PermissionDenied
from django.db.models import Case, Count, F, Q, QuerySet, When
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
from oncalendar import OnCalendar, OnCalendarError
from pydantic import BaseModel, TypeAdapter, ValidationError

from hc.accounts.http import AuthenticatedHttpRequest
from hc.accounts.models import Member, Profile, Project
from hc.api.models import (
    DEFAULT_GRACE,
    DEFAULT_TIMEOUT,
    MAX_DURATION,
    Channel,
    Check,
    Flip,
    Notification,
    Ping,
    TokenBucket,
)
from hc.api.transports import Signal, Telegram, TransportError
from hc.front import forms
from hc.front.decorators import require_setting
from hc.front.templatetags.hc_extras import (
    down_title,
    num_down_title,
    site_hostname,
    sortchecks,
)
from hc.lib import curl
from hc.lib.badges import get_badge_url
from hc.lib.tz import all_timezones

logger = logging.getLogger(__name__)

VALID_SORT_VALUES = ("name", "-name", "last_ping", "-last_ping", "created")
STATUS_TEXT_TMPL = get_template("front/log_status_text.html")
LAST_PING_TMPL = get_template("front/last_ping_cell.html")
EVENTS_TMPL = get_template("front/details_events.html")
DOWNTIMES_TMPL = get_template("front/details_downtimes.html")


def _tags_counts(checks: Iterable[Check]) -> tuple[list[tuple[str, str, str]], int]:
    num_down = 0
    grace = set()
    counts: Counter[str] = Counter()
    down_counts: Counter[str] = Counter()
    for check in checks:
        status = check.get_status()
        counts.update(check.tags_list())
        if status == "down":
            num_down += 1
            down_counts.update(check.tags_list())
        elif status == "grace":
            grace.update(check.tags_list())

    result = []
    for tag in counts:
        if tag in down_counts:
            status = "down"
            text = f"{down_counts[tag]} of {counts[tag]} down"
        else:
            status = "grace" if tag in grace else "up"
            text = f"{counts[tag]} up"

        result.append((tag, status, text))

    return result, num_down


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


def _refresh_last_active_date(profile: Profile) -> None:
    """Update last_active_date if it is more than a day old."""

    if profile.last_active_date is None or (now() - profile.last_active_date).days > 0:
        profile.last_active_date = now()
        profile.save()

    return None


def _get_referer_qs(request: HttpRequest) -> str:
    parsed = urlparse(request.META.get("HTTP_REFERER", ""))
    if parsed.query:
        assert isinstance(parsed.query, str)
        return "?" + parsed.query
    return ""


@login_required
def checks(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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

    tags_counts, num_down = _tags_counts(checks)
    tags_counts.sort(key=lambda item: item[0].lower())

    is_group = Case(When(kind="group", then=0), default=1)
    channels = project.channel_set.annotate(is_group=is_group)
    # Sort groups first, then in the creation order
    channels = channels.order_by("is_group", "created")

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
        "tags": tags_counts,
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

    return render(request, "front/checks.html", ctx)


@login_required
def status(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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

    tags_counts, num_down = _tags_counts(checks)
    tags = {tag: (status, tooltip) for tag, status, tooltip in tags_counts}
    return JsonResponse(
        {"details": details, "tags": tags, "title": num_down_title(num_down)}
    )


@login_required
@require_POST
def switch_channel(
    request: AuthenticatedHttpRequest, code: UUID, channel_code: UUID
) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    channel = get_object_or_404(Channel, code=channel_code)
    if channel.project_id != check.project_id:
        return HttpResponseBadRequest()

    if request.POST.get("state") == "on":
        channel.checks.add(check)
    else:
        channel.checks.remove(check)

    return HttpResponse()


class ProjectStatus(TypedDict):
    status: str
    started: bool


def _get_project_summary(profile: Profile) -> dict[UUID, ProjectStatus]:
    statuses: dict[UUID, ProjectStatus] = defaultdict(
        lambda: {"status": "up", "started": False}
    )
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


def index(request: HttpRequest) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect("hc-login")

    request = cast(AuthenticatedHttpRequest, request)
    summary = _get_project_summary(request.profile)
    if "refresh" in request.GET:
        return JsonResponse({str(k): v for k, v in summary.items()})

    q = request.profile.projects()
    q = q.annotate(n_checks=Count("check", distinct=True))
    q = q.annotate(n_channels=Count("channel", distinct=True))
    q = q.annotate(owner_email=F("owner__email"))
    projects = list(q)
    any_down = False
    for project in projects:
        setattr(project, "overall_status", summary[project.code]["status"])
        setattr(project, "any_started", summary[project.code]["started"])
        if summary[project.code]["status"] == "down":
            any_down = True

    # The list returned by projects() is already sorted . Do an additional sorting pass
    # to move projects with overall_status=down to the front (without changing their
    # relative order)
    projects.sort(key=lambda p: getattr(p, "overall_status") != "down")

    ctx = {
        "page": "projects",
        "projects": projects,
        "last_project_id": request.session.get("last_project_id"),
        "any_down": any_down,
    }

    return render(request, "front/projects.html", ctx)


@login_required
def projects_menu(request: AuthenticatedHttpRequest) -> HttpResponse:
    projects = list(request.profile.projects())

    statuses: dict[int, str] = defaultdict(lambda: "up")
    for check in Check.objects.filter(project__in=projects):
        old_status = statuses[check.project_id]
        if old_status != "down":
            status = check.get_status()
            if status == "down" or (status == "grace" and old_status == "up"):
                statuses[check.project_id] = status

    for p in projects:
        setattr(p, "overall_status", statuses[p.id])

    return render(request, "front/projects_menu.html", {"projects": projects})


def dashboard(request: HttpRequest) -> HttpResponse:
    return render(request, "front/dashboard.html", {})


def _replace_placeholders(doc: str, html: str) -> str:
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


def serve_doc(request: HttpRequest, doc: str = "introduction") -> HttpResponse:
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
def docs_search(request: HttpRequest) -> HttpResponse:
    form = forms.SearchForm(request.GET)
    if not form.is_valid():
        return render(request, "front/docs_search.html", {"results": []})

    query = """
        SELECT slug, title, snippet(docs, 2, '<span>', '</span>', '&hellip;', 10)
        FROM docs
        WHERE docs MATCH ?
        ORDER BY bm25(docs, 2.0, 10.0, 1.0)
        LIMIT 8
    """

    # Wrap the query in double quotes to get a valid FTS string
    # https://www.sqlite.org/fts5.html#full_text_query_syntax
    q = '"%s"' % form.cleaned_data["q"]
    con = sqlite3.connect(settings.BASE_DIR / "search.db")
    cur = con.cursor()
    res = cur.execute(query, (q,))

    ctx = {"results": res.fetchall()}
    return render(request, "front/docs_search.html", ctx)


def docs_cron(request: HttpRequest) -> HttpResponse:
    return render(request, "front/docs_cron.html", {"page": "docs-cron"})


@require_POST
@login_required
def add_check(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def update_name(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def filtering_rules(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def update_timeout(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    kind = request.POST.get("kind")
    if kind == "simple":
        simple_form = forms.TimeoutForm(request.POST)
        if not simple_form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "simple"
        check.timeout = simple_form.cleaned_data["timeout"]
        check.grace = simple_form.cleaned_data["grace"]
    elif kind == "cron":
        cron_form = forms.CronForm(request.POST)
        if not cron_form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "cron"
        check.schedule = cron_form.cleaned_data["schedule"]
        check.tz = cron_form.cleaned_data["tz"]
        check.grace = cron_form.cleaned_data["grace"]
    elif kind == "oncalendar":
        oncalendar_form = forms.OnCalendarForm(request.POST)
        if not oncalendar_form.is_valid():
            return HttpResponseBadRequest()

        check.kind = "oncalendar"
        check.schedule = oncalendar_form.cleaned_data["schedule"]
        check.tz = oncalendar_form.cleaned_data["tz"]
        check.grace = oncalendar_form.cleaned_data["grace"]

    check.alert_after = check.going_down_after()
    if check.status == "up":
        assert check.alert_after
        if check.alert_after < now():
            # Checks can flip from "up" to "down" state as a result of changing check's
            # schedule.  We don't want to send notifications when changing schedule
            # interactively in the web UI. So we update the `alert_after` and `status`
            # fields, and create a Flip object here the same way as `sendalerts` would
            # do, but without sending an actual alert.
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
def cron_preview(request: HttpRequest) -> HttpResponse:
    schedule = request.POST.get("schedule", "")
    tz = request.POST.get("tz")
    ctx: dict[str, object] = {"tz": tz, "dates": []}

    if tz not in all_timezones:
        ctx["bad_tz"] = True
        return render(request, "front/cron_preview.html", ctx)

    now_local = now().astimezone(ZoneInfo(tz))
    try:
        it = CronSim(schedule, now_local)
        for i in range(0, 6):
            assert isinstance(ctx["dates"], list)
            ctx["dates"].append(next(it))
        ctx["desc"] = it.explain()
    except (CronSimError, StopIteration):
        ctx["bad_schedule"] = True

    return render(request, "front/cron_preview.html", ctx)


@require_POST
@login_required
def oncalendar_preview(request: HttpRequest) -> HttpResponse:
    schedule = request.POST.get("schedule", "")
    tz = request.POST.get("tz")
    ctx: dict[str, object] = {"tz": tz, "dates": []}

    if tz not in all_timezones:
        ctx["bad_tz"] = True
        return render(request, "front/oncalendar_preview.html", ctx)

    now_local = now().astimezone(ZoneInfo(tz))
    try:
        it = OnCalendar(schedule, now_local)
        iterations = 6 if tz == "UTC" else 4
        for i in range(0, iterations):
            assert isinstance(ctx["dates"], list)
            ctx["dates"].append(next(it))
    except (OnCalendarError, StopIteration):
        if not ctx["dates"]:
            ctx["bad_schedule"] = True

    return render(request, "front/oncalendar_preview.html", ctx)


def validate_schedule(request: HttpRequest) -> HttpResponse:
    kind = request.GET.get("kind", "")
    iterator: type[CronSim] | type[OnCalendar]
    if kind == "cron":
        iterator = CronSim
    elif kind == "oncalendar":
        iterator = OnCalendar
    else:
        return HttpResponseBadRequest()

    schedule = request.GET.get("schedule", "")
    result = True
    try:
        # Does cronsim/oncalendar accept the schedule?
        it = iterator(schedule, now())
        # Can it calculate the next datetime?
        next(it)
    except (CronSimError, OnCalendarError, StopIteration):
        result = False

    return JsonResponse({"result": result})


@login_required
def ping_details(
    request: AuthenticatedHttpRequest, code: UUID, n: int | None = None
) -> HttpResponse:
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

    if ping.scheme == "email" and body:
        parsed = email.message_from_string(body, policy=email.policy.SMTP)
        assert isinstance(parsed, EmailMessage)
        ctx["subject"] = parsed.get("subject", "")

        # The "active" tab is set to show the value that's successfully parsed last.
        # Per the current implementation, this means that if both plain text and HTML
        # content are present, the ping details dialog will initially display the HTML
        # content, otherwise - only one content type exists, and we default to that
        # (either plain text or HTML, at least one of them should exist in a
        # valid email).
        #
        # NOTE: If both plain text and html have not been parsed successfully the
        # "active" tab is not set at all, but currently this is not an issue since in
        # this case the "ping details" template does not render any tabs.

        plain_mime_part = parsed.get_body(("plain",))
        if plain_mime_part:
            assert isinstance(plain_mime_part, EmailMessage)
            ctx["plain"] = plain_mime_part.get_content()
            ctx["active"] = "plain"

        html_mime_part = parsed.get_body(("html",))
        if html_mime_part:
            assert isinstance(html_mime_part, EmailMessage)
            ctx["html"] = html_mime_part.get_content()
            ctx["active"] = "html"

    return render(request, "front/ping_details.html", ctx)


@login_required
def ping_body(request: AuthenticatedHttpRequest, code: UUID, n: int) -> HttpResponse:
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
def pause(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def resume(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def remove_check(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check = _get_rw_check_for_user(request, code)

    project = check.project
    check.lock_and_delete()
    return redirect("hc-checks", project.code)


@require_POST
@login_required
def clear_events(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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


def _get_events(
    check: Check,
    page_limit: int,
    start: datetime,
    end: datetime,
    kinds: tuple[str, ...] | None = None,
) -> list[Notification | Ping | Flip]:
    # Sorting by "n" instead of "id" is important here. Both give the same
    # query results, but sorting by "id" can cause postgres to pick
    # api_ping.id index (slow if the api_ping table is big). Sorting by
    # "n" works around the problem--postgres picks the api_ping.owner_id index.
    pq = check.visible_pings.order_by("-n")
    pq = pq.filter(created__gte=start, created__lte=end)
    if kinds is not None:
        kinds_filter = Q(kind__in=kinds)
        if "success" in kinds:
            kinds_filter = kinds_filter | Q(kind__isnull=True) | Q(kind="")
        pq = pq.filter(kinds_filter)

    pings = list(pq[:page_limit])

    # Optimization: the template will access Ping.duration, which would generate a
    # SQL query per displayed ping. Since we've already fetched a list of pings,
    # for some of them we can calculate durations more efficiently, without causing
    # additional SQL queries:
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
                matching_start = starts[ping.rid]
                if matching_start is not None:
                    if ping.created - matching_start < MAX_DURATION:
                        ping.duration = ping.created - matching_start

            starts[ping.rid] = None

    # If we will need to fall back to Ping.duration() more than 10 times
    # then disable duration display altogether:
    if num_misses > 10:
        for ping in pings:
            ping.duration = None

    alerts: list[Notification] = []
    if kinds and "notification" in kinds:
        aq = check.notification_set.order_by("-created")
        aq = aq.filter(created__gte=start, created__lte=end, check_status="down")
        aq = aq.select_related("channel")
        alerts = list(aq[:page_limit])

    flips: list[Flip] = []
    if kinds is None or "flip" in kinds:
        fq = check.flip_set.order_by("-created")
        fq = fq.filter(created__gte=start, created__lte=end)
        flips = list(fq[:page_limit])

    events = pings + alerts + flips
    # Sort events by the timestamp.
    # If timestamps are equal, put flips chronologically after pings
    events.sort(key=lambda el: (el.created, isinstance(el, Flip)), reverse=True)
    return events[:page_limit]


@login_required
def log(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    smin = check.created
    smax = now()
    oldest_ping = check.visible_pings.order_by("n").first()
    if oldest_ping:
        smin = max(smin, oldest_ping.created)

    events = _get_events(check, 1000, start=smin, end=smax)
    ctx = {
        "page": "log",
        "project": check.project,
        "check": check,
        "min": smin,
        "max": smax,
        "events": events,
        "oldest_ping": oldest_ping,
    }

    if events:
        # A full precision timestamp of the most recent event.
        # This will be used client-side for fetching live updates to specify
        # "return any events after *this* point".
        ctx["last_event_timestamp"] = events[0].created.timestamp()

    return render(request, "front/log.html", ctx)


@login_required
def details(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    _refresh_last_active_date(request.profile)
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    if request.GET.get("urls") in ("uuid", "slug") and rw:
        check.project.show_slugs = request.GET["urls"] == "slug"
        check.project.save()

    all_channels = check.project.channel_set.order_by("created")
    regular_channels: list[Channel] = []
    group_channels: list[Channel] = []
    for channel in all_channels:
        channels = group_channels if channel.kind == "group" else regular_channels
        channels.append(channel)

    all_tags = set()
    q = Check.objects.filter(project=check.project).exclude(tags="")
    for tags in q.values_list("tags", flat=True):
        all_tags.update(tags.split(" "))

    ctx = {
        "page": "details",
        "project": check.project,
        "check": check,
        "rw": rw,
        "channels": regular_channels,
        "group_channels": group_channels,
        "enabled_channels": list(check.channel_set.all()),
        "timezones": all_timezones,
        "downtimes": check.downtimes(3, request.profile.tz),
        "tz": request.profile.tz,
        "is_copied": "copied" in request.GET,
        "all_tags": " ".join(sorted(all_tags)),
    }

    return render(request, "front/details.html", ctx)


@login_required
def uncloak(request: AuthenticatedHttpRequest, unique_key: str) -> HttpResponse:
    for check in request.profile.checks_from_all_projects().only("code"):
        if check.unique_key == unique_key:
            return redirect("hc-details", check.code)

    raise Http404("not found")


@login_required
def transfer(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def copy(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def status_single(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)

    status = check.get_status()
    events = _get_events(check, 30, start=check.created, end=now())
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
def badges(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project, rw = _get_project_for_user(request, code)

    if request.method == "POST":
        form = forms.BadgeSettingsForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        fmt = form.cleaned_data["fmt"]
        states = form.cleaned_data["states"]
        with_late = True if states == "3" else False
        if form.cleaned_data["target"] == "all":
            label = settings.MASTER_BADGE_LABEL
            url = get_badge_url(project.badge_key, "*", fmt, with_late)
        elif form.cleaned_data["target"] == "tag":
            label = form.cleaned_data["tag"]
            url = get_badge_url(project.badge_key, label, fmt, with_late)
        elif form.cleaned_data["target"] == "check":
            check = project.check_set.get(code=form.cleaned_data["check"])
            url = settings.SITE_ROOT + reverse(
                "hc-badge-check", args=[states, check.prepare_badge_key(), fmt]
            )
            label = check.name_then_code()

        if fmt == "shields":
            url = "https://img.shields.io/endpoint?" + urlencode({"url": url})

        ctx = {"fmt": fmt, "label": label, "url": url}
        return render(request, "front/badges_preview.html", ctx)

    checks = list(project.check_set.order_by("name"))
    tags = set()
    for check in checks:
        tags.update(check.tags_list())

    sorted_tags = sorted(tags, key=lambda s: s.lower())

    ctx = {
        "project": project,
        "page": "badges",
        "checks": checks,
        "tags": sorted_tags,
        "fmt": "svg",
        "label": settings.MASTER_BADGE_LABEL,
        "url": get_badge_url(project.badge_key, "*"),
    }
    return render(request, "front/badges.html", ctx)


@login_required
def channels(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project, rw = _get_project_for_user(request, code)

    if request.method == "POST":
        if not rw:
            return HttpResponseForbidden()

        channel_code = request.POST["channel"]
        try:
            channel = Channel.objects.get(code=channel_code)
        except Channel.DoesNotExist:
            return HttpResponseBadRequest()
        if channel.project_id != project.id:
            return HttpResponseForbidden()

        new_checks = []
        for key in request.POST:
            if key.startswith("check-"):
                check_code = key[6:]
                try:
                    check = Check.objects.get(code=check_code)
                except Check.DoesNotExist:
                    return HttpResponseBadRequest()
                if check.project_id != project.id:
                    return HttpResponseForbidden()
                new_checks.append(check)

        channel.checks.set(new_checks)
        return redirect("hc-channels", project.code)

    channels = project.channel_set.annotate(n_checks=Count("checks"))
    # Sort groups first, then in the creation order
    channels = channels.annotate(is_group=Case(When(kind="group", then=0), default=1))
    channels = channels.order_by("is_group", "created")

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
def channel_checks(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)

    assigned = set(channel.checks.values_list("code", flat=True).distinct())
    checks = channel.project.check_set.order_by("created")
    ctx = {"checks": checks, "assigned": assigned, "channel": channel}

    return render(request, "front/channel_checks.html", ctx)


@require_POST
@login_required
def update_channel_name(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)

    form = forms.ChannelNameForm(request.POST)
    if form.is_valid():
        channel.name = form.cleaned_data["name"]
        channel.save()

    return redirect("hc-channels", channel.project.code)


def verify_email(request: HttpRequest, code: UUID, token: str) -> HttpResponse:
    channel = get_object_or_404(Channel, code=code)
    if channel.make_token() == token:
        channel.email_verified = True
        channel.save()
        return render(request, "front/verify_email_success.html")

    return render(request, "bad_link.html")


@csrf_exempt
def unsubscribe_email(
    request: HttpRequest, code: UUID, signed_token: str
) -> HttpResponse:
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
def send_test_notification(
    request: AuthenticatedHttpRequest, code: UUID
) -> HttpResponse:
    channel, rw = _get_channel_for_user(request, code)

    dummy = Check(name="TEST", status="down", project=channel.project)
    dummy.last_ping = now() - td(days=1)
    dummy.n_pings = 42

    dummy_flip = Flip(owner=dummy)
    dummy_flip.created = now()
    dummy_flip.old_status = "up"
    dummy_flip.new_status = "down"

    # Delete all older test notifications for this channel
    Notification.objects.filter(channel=channel, owner=None).delete()

    # Send the test notification
    error = channel.notify(dummy_flip, is_test=True)

    if error == "no-op":
        # This channel may be configured to send "up" notifications only.
        dummy_flip.old_status = "down"
        dummy_flip.new_status = "up"
        error = channel.notify(dummy_flip, is_test=True)

    if error:
        messages.warning(request, "Could not send a test notification. %s." % error)
    else:
        messages.success(request, "Test notification sent!")

    return redirect("hc-channels", channel.project.code)


@require_POST
@login_required
def remove_channel(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
            if channel.disabled or form.cleaned_data["value"] != channel.email.value:
                channel.disabled = False

                if not settings.EMAIL_USE_VERIFICATION:
                    # In self-hosted setting, administrator can set
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
                "value": channel.email.value,
                "up": channel.email.notify_up,
                "down": channel.email.notify_down,
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
def add_email(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="email")
    return email_form(request, channel)


@login_required
def edit_channel(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    channel = _get_rw_channel_for_user(request, code)
    if channel.kind == "email":
        return email_form(request, channel)
    elif channel.kind == "webhook":
        return webhook_form(request, channel)
    elif channel.kind == "sms":
        return sms_form(request, channel)
    elif channel.kind == "signal":
        return signal_form(request, channel)
    elif channel.kind == "whatsapp":
        return whatsapp_form(request, channel)
    elif channel.kind == "ntfy":
        return ntfy_form(request, channel)
    elif channel.kind == "group":
        return group_form(request, channel)

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

        def flatten(d: dict[str, str]) -> str:
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
def add_webhook(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="webhook")
    return webhook_form(request, channel)


@require_setting("SHELL_ENABLED")
@login_required
def add_shell(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_pd(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_pd_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
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
def pd_help(request: HttpRequest) -> HttpResponse:
    ctx = {"page": "channels"}
    return render(request, "integrations/add_pd_simple.html", ctx)


@require_setting("PAGERTREE_ENABLED")
@login_required
def add_pagertree(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_slack(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def slack_help(request: HttpRequest) -> HttpResponse:
    ctx = {"page": "channels"}
    return render(request, "integrations/add_slack_btn.html", ctx)


@require_setting("SLACK_ENABLED")
@require_setting("SLACK_CLIENT_ID")
@login_required
def add_slack_btn(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_slack_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
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
    if not isinstance(doc, dict) or not doc.get("ok"):
        messages.warning(
            request,
            "Received an unexpected response from Slack. Integration not added.",
        )
        logger.warning("Unexpected Slack OAuth response: %s", result.content)
        return redirect("hc-channels", project.code)

    channel = Channel(kind="slack", project=project)
    channel.value = result.text
    channel.save()
    channel.assign_all_checks()

    messages.success(request, "Success, integration added!")
    return redirect("hc-channels", project.code)


@require_setting("MATTERMOST_ENABLED")
def mattermost_help(request: HttpRequest) -> HttpResponse:
    return render(request, "integrations/add_mattermost.html")


@require_setting("MATTERMOST_ENABLED")
@login_required
def add_mattermost(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def rocketchat_help(request: HttpRequest) -> HttpResponse:
    return render(request, "integrations/add_rocketchat.html")


@require_setting("ROCKETCHAT_ENABLED")
@login_required
def add_rocketchat(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_pushbullet(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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


class PushbulletOAuthResponse(BaseModel):
    access_token: str


@require_setting("PUSHBULLET_CLIENT_ID")
@login_required
def add_pushbullet_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
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
    try:
        doc = PushbulletOAuthResponse.model_validate_json(result.content, strict=True)
    except ValidationError:
        logger.warning("Unexpected Pushbullet OAuth response: %s", result.content)
        messages.warning(
            request,
            "Received an unexpected response from Pushbullet. Integration not added.",
        )
        return redirect("hc-channels", project.code)

    channel = Channel(kind="pushbullet", project=project)
    channel.value = doc.access_token
    channel.save()
    channel.assign_all_checks()
    messages.success(request, "The Pushbullet integration has been added!")
    return redirect("hc-channels", project.code)


@require_setting("DISCORD_CLIENT_ID")
@login_required
def add_discord(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_discord_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
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
    if not isinstance(doc, dict) or "access_token" not in doc:
        messages.warning(
            request,
            "Received an unexpected response from Discord. Integration not added.",
        )
        logger.warning("Unexpected Discord OAuth response: %s", result.content)
        return redirect("hc-channels", project.code)

    channel = Channel(kind="discord", project=project)
    channel.value = result.text
    channel.save()
    channel.assign_all_checks()
    messages.success(request, "The Discord integration has been added!")
    return redirect("hc-channels", project.code)


@require_setting("PUSHOVER_API_TOKEN")
def pushover_help(request: HttpRequest) -> HttpResponse:
    ctx = {"page": "channels"}
    return render(request, "integrations/add_pushover_help.html", ctx)


@require_setting("PUSHOVER_API_TOKEN")
@login_required
def add_pushover(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)

    if request.method == "POST":
        state = token_urlsafe().lower()

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
        assert settings.PUSHOVER_SUBSCRIPTION_URL
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
def add_opsgenie(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_victorops(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_zulip(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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


class TelegramChat(BaseModel):
    id: int
    type: Literal["group", "private", "supergroup", "channel"]
    title: str | None = None
    username: str | None = None


class TelegramMessage(BaseModel):
    chat: TelegramChat
    text: str
    message_thread_id: int | None = None


class TelegramCallback(BaseModel):
    message: TelegramMessage

    @classmethod
    def load(self, data: bytes) -> TelegramCallback:
        doc = json.loads(data.decode())
        if "channel_post" in doc:
            # Telegram's "channel_post" key uses the same structure as "message".
            # To keep the validation and view logic simple, if the payload
            # contains "channel_post", copy it to "message", and proceed as usual.
            doc["message"] = doc["channel_post"]
        return TelegramCallback.model_validate(doc, strict=True)


@csrf_exempt
@require_POST
def telegram_bot(request: HttpRequest) -> HttpResponse:
    try:
        doc = TelegramCallback.load(request.body)
    except ValidationError:
        # We don't recognize the message format, but don't want Telegram
        # retrying this over and over again, so respond with 200 OK
        return HttpResponse()
    except ValueError:
        return HttpResponseBadRequest()

    if "/start" not in doc.message.text:
        return HttpResponse()

    chat = doc.message.chat
    recipient = {
        "id": chat.id,
        "type": chat.type,
        "name": chat.title or chat.username,
        "thread_id": doc.message.message_thread_id,
    }

    invite = render_to_string(
        "integrations/telegram_invite.html",
        {"qs": signing.dumps(recipient)},
    )

    try:
        Telegram.send(chat.id, doc.message.message_thread_id, invite)
    except TransportError:
        # Swallow the error and return HTTP 200 OK, otherwise Telegram will
        # hit the webhook again and again.
        pass

    return HttpResponse()


@require_setting("TELEGRAM_TOKEN")
def telegram_help(request: HttpRequest) -> HttpResponse:
    ctx = {
        "page": "channels",
        "bot_name": settings.TELEGRAM_BOT_NAME,
    }

    return render(request, "integrations/add_telegram.html", ctx)


@require_setting("TELEGRAM_TOKEN")
@login_required
def add_telegram(request: AuthenticatedHttpRequest) -> HttpResponse:
    recipient = None
    if qs := request.META["QUERY_STRING"]:
        try:
            recipient = signing.loads(qs, max_age=600)
            assert isinstance(recipient, dict)
        except signing.BadSignature:
            return render(request, "bad_link.html")

    if request.method == "POST":
        form = forms.AddTelegramForm(request.POST)
        if not form.is_valid():
            return HttpResponseBadRequest()

        project = _get_rw_project_for_user(request, form.cleaned_data["project"])
        channel = Channel(project=project, kind="telegram")
        channel.value = json.dumps(recipient)
        channel.save()

        channel.assign_all_checks()
        messages.success(request, "The Telegram integration has been added!")
        return redirect("hc-channels", project.code)

    ctx = {
        "page": "channels",
        "projects": request.profile.projects(),
        "recipient": recipient,
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
                "phone": channel.phone.value,
                "up": channel.phone.notify_up,
                "down": channel.phone.notify_down,
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
def add_sms(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="sms")
    return sms_form(request, channel)


@require_setting("TWILIO_AUTH")
@login_required
def add_call(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
                "phone": channel.phone.value,
                "up": channel.phone.notify_up,
                "down": channel.phone.notify_down,
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
def add_whatsapp(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
                "phone": channel.phone.value,
                "up": channel.phone.notify_up,
                "down": channel.phone.notify_down,
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
def add_signal(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="signal")
    return signal_form(request, channel)


@require_setting("TRELLO_APP_KEY")
@login_required
def add_trello(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_matrix(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_apprise(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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


class TrelloList(BaseModel):
    id: str
    name: str


class TrelloBoard(BaseModel):
    id: str
    name: str
    lists: list[TrelloList]


TrelloBoards = TypeAdapter(list[TrelloBoard])


@require_setting("TRELLO_APP_KEY")
@login_required
@require_POST
def trello_settings(request: AuthenticatedHttpRequest) -> HttpResponse:
    token = request.POST.get("token", "")

    url = "https://api.trello.com/1/members/me/boards"
    assert settings.TRELLO_APP_KEY
    params = {
        "key": settings.TRELLO_APP_KEY,
        "token": token,
        "filter": "open",
        "fields": "id,name",
        "lists": "open",
        "list_fields": "id,name",
    }

    result = curl.get(url, params)
    try:
        boards = TrelloBoards.validate_json(result.content)
    except ValidationError:
        logger.warning("Unexpected Trello API response: %s", result.content)
        return render(request, "integrations/trello_settings.html", {"error": 1})

    num_lists = sum(len(board.lists) for board in boards)
    ctx = {"token": token, "boards": boards, "num_lists": num_lists}
    return render(request, "integrations/trello_settings.html", ctx)


@require_setting("MSTEAMS_ENABLED")
@login_required
def add_msteams(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_prometheus(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project, rw = _get_project_for_user(request, code)
    ctx = {
        "page": "channels",
        "project": project,
        "site_scheme": urlparse(settings.SITE_ROOT).scheme,
    }
    return render(request, "integrations/add_prometheus.html", ctx)


@require_setting("PROMETHEUS_ENABLED")
def metrics(request: HttpRequest, code: UUID, key: str) -> HttpResponse:
    if len(key) != 32:
        return HttpResponseBadRequest()

    q = Project.objects.filter(code=code, api_key_readonly=key)
    try:
        project = q.get()
    except Project.DoesNotExist:
        return HttpResponseForbidden()

    checks = Check.objects.filter(project_id=project.id).order_by("id")

    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

    def output(checks: QuerySet[Check]) -> Iterable[str]:
        help = "Whether the check is currently up (1 for yes, 0 for no)."
        yield f"# HELP hc_check_up {help}\n"
        yield "# TYPE hc_check_up gauge\n"

        TMPL = """hc_check_up{name="%s", tags="%s", unique_key="%s"} %d\n"""
        for check in checks:
            value = 0 if check.get_status() == "down" else 1
            yield TMPL % (esc(check.name), esc(check.tags), check.unique_key, value)

        yield "\n"
        help = "Whether the check is currently started (1 for yes, 0 for no)."
        yield f"# HELP hc_check_started {help}\n"
        yield "# TYPE hc_check_started gauge\n"
        TMPL = """hc_check_started{name="%s", tags="%s", unique_key="%s"} %d\n"""
        for check in checks:
            value = 1 if check.last_start is not None else 0
            yield TMPL % (esc(check.name), esc(check.tags), check.unique_key, value)

        all_tags, down_tags, num_down = set(), set(), 0
        for check in checks:
            all_tags.update(check.tags_list())
            if check.get_status() == "down":
                num_down += 1
                down_tags.update(check.tags_list())

        yield "\n"
        help = "Whether all checks with this tag are up (1 for yes, 0 for no)."
        yield f"# HELP hc_tag_up {help}\n"
        yield "# TYPE hc_tag_up gauge\n"
        TMPL = """hc_tag_up{tag="%s"} %d\n"""
        for tag in sorted(all_tags):
            value = 0 if tag in down_tags else 1
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
def add_spike(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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
def add_linenotify(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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


class LineTokenResponse(BaseModel):
    status: Literal[200]
    access_token: str


class LineStatusResponse(BaseModel):
    target: str


@require_setting("LINENOTIFY_CLIENT_ID")
@login_required
def add_linenotify_complete(request: AuthenticatedHttpRequest) -> HttpResponse:
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
    try:
        tr = LineTokenResponse.model_validate_json(result.content, strict=True)
        token = tr.access_token
    except ValidationError:
        messages.warning(request, "Received an unexpected response from LINE Notify.")
        logger.warning("Unexpected LINE OAuth response: %s", result.content)
        return redirect("hc-channels", project.code)

    # Fetch notification target's name, will use it as channel name:
    headers = {"Authorization": f"Bearer {token}"}
    result = curl.get("https://notify-api.line.me/api/status", headers=headers)
    try:
        sr = LineStatusResponse.model_validate_json(result.content, strict=True)
        target = sr.target
    except ValidationError:
        messages.warning(request, "Received an unexpected response from LINE Notify.")
        logger.warning("Unexpected LINE Status response: %s", result.content)
        return redirect("hc-channels", project.code)

    channel = Channel(kind="linenotify", project=project)
    channel.name = target
    channel.value = token
    channel.save()
    channel.assign_all_checks()
    messages.success(request, "The LINE Notify integration has been added!")

    return redirect("hc-channels", project.code)


@login_required
def add_gotify(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
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


def group_form(request: HttpRequest, channel: Channel) -> HttpResponse:
    adding = channel._state.adding
    if request.method == "POST":
        form = forms.GroupForm(request.POST, project=channel.project)
        if form.is_valid():
            channel.name = form.cleaned_data["label"]
            channel.value = form.get_value()
            channel.save()

            if adding:
                channel.assign_all_checks()
            return redirect("hc-channels", channel.project.code)
    elif adding:
        form = forms.GroupForm(project=channel.project)
    else:
        # Filter out unavailable channels
        channels = list(channel.group_channels.values_list("code", flat=True))
        form = forms.GroupForm(
            {"channels": channels, "label": channel.name}, project=channel.project
        )

    ctx = {"page": "channels", "project": channel.project, "form": form}
    return render(request, "integrations/group_form.html", ctx)


@login_required
def add_group(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="group")
    return group_form(request, channel)


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
                "topic": channel.ntfy.topic,
                "url": channel.ntfy.url,
                "priority": channel.ntfy.priority,
                "priority_up": channel.ntfy.priority_up,
                "token": channel.ntfy.token,
            }
        )

    ctx = {"page": "channels", "project": channel.project, "form": form}
    return render(request, "integrations/ntfy_form.html", ctx)


@login_required
def add_ntfy(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project = _get_rw_project_for_user(request, code)
    channel = Channel(project=project, kind="ntfy")
    return ntfy_form(request, channel)


@require_setting("SIGNAL_CLI_SOCKET")
@login_required
def signal_captcha(request: AuthenticatedHttpRequest) -> HttpResponse:
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
        for reply_bytes in Signal._read_replies(payload_bytes):
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
def verify_signal_number(request: AuthenticatedHttpRequest) -> HttpResponse:
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
        Signal.send(phone, f"Test message from {settings.SITE_NAME}")
    except TransportError as e:
        return render_result(e.message)

    # Success!
    return render_result(None)


@login_required
def log_events(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    check, rw = _get_check_for_user(request, code, preload_owner_profile=True)
    form = forms.LogFiltersForm(request.GET)
    if not form.is_valid():
        return HttpResponseBadRequest()

    if form.cleaned_data["u"]:
        # We are live-loading more events
        start = form.cleaned_data["u"] + td(microseconds=1)
        end = now()
    else:
        # We're applying new filters
        start = check.created
        end = form.cleaned_data["end"] or now()

    # clamp start to the date of the oldest visible ping
    oldest_ping = check.visible_pings.order_by("n").first()
    if oldest_ping:
        start = max(start, oldest_ping.created)

    events = _get_events(check, 1000, start=start, end=end, kinds=form.kinds())
    ctx = {
        "events": events,
        "describe_body": True,
    }
    response = render(request, "front/log_rows.html", ctx)

    if events:
        # Include a full precision timestamp of the most recent event in a
        # response header. This will be used client-side for fetching live updates
        # to specify "return any events after *this* point".
        response["X-Last-Event-Timestamp"] = str(events[0].created.timestamp())
    return response


# Forks: add custom views after this line
