from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse
from uuid import UUID

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import QuerySet
from django.http import (
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
)
from django.shortcuts import render
from hc.accounts.http import AuthenticatedHttpRequest
from hc.accounts.models import Project
from hc.api.models import Check
from hc.front.decorators import require_setting
from hc.front.views import _get_project_for_user


@require_setting("PROMETHEUS_ENABLED")
@login_required
def add_prometheus(request: AuthenticatedHttpRequest, code: UUID) -> HttpResponse:
    project, rw = _get_project_for_user(request, code)
    ctx = {
        "page": "channels",
        "project": project,
        "site_scheme": urlparse(settings.SITE_ROOT).scheme,
    }
    return render(request, "add_prometheus.html", ctx)


@require_setting("PROMETHEUS_ENABLED")
def metrics(request: HttpRequest, code: UUID, key: str | None = None) -> HttpResponse:
    if key is None:
        # If key was not in the URL, expect it in the Authorization request header
        key = request.META.get("HTTP_AUTHORIZATION", "")
        if not key.startswith("Bearer "):
            return HttpResponse(status=401)

        key = key.lstrip("Bearer ")

    if len(key) != 32:
        return HttpResponseBadRequest()

    project = Project.objects.for_api_key(key, accept_rw=False, accept_ro=True)
    if project is None:
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
