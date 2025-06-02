from __future__ import annotations

import json
from functools import wraps
from typing import Any, Callable

from django.db.models import Q
from django.http import HttpRequest, HttpResponse, JsonResponse

from hc.accounts.models import Project
from hc.lib.typealias import ViewFunc


class ApiRequest(HttpRequest):
    json: dict[Any, Any]
    project: Project
    readonly: bool
    v: int


def error(msg: str, status: int = 400) -> JsonResponse:
    return JsonResponse({"error": msg}, status=status)


def _get_api_version(request: HttpRequest) -> int:
    if request.path_info.startswith("/api/v3/"):
        return 3
    if request.path_info.startswith("/api/v2/"):
        return 2
    return 1


def lookup_project(api_key: str, require_rw: bool) -> Project | None:
    """Look up project by API key.

    This handles both the old plain text API keys, and the new hashed API keys.
    For the hashed API keys, it looks up project by the first 8 characters of the
    random part of the key, then calls Project.compare_api_key().
    """

    # Hashed keys
    if api_key.startswith("hcw_"):
        secret8 = api_key[4:12]
        for project in Project.objects.filter(api_key__startswith=secret8):
            if project.compare_api_key(api_key):
                return project

    if not require_rw and api_key.startswith("hcr_"):
        secret8 = api_key[4:12]
        for project in Project.objects.filter(api_key_readonly__startswith=secret8):
            if project.compare_api_key(api_key):
                return project

    # Plain text keys
    if require_rw:
        try:
            return Project.objects.get(api_key=api_key)
        except Project.DoesNotExist:
            pass
    else:
        write_key_match = Q(api_key=api_key)
        read_key_match = Q(api_key_readonly=api_key)
        try:
            return Project.objects.get(write_key_match | read_key_match)
        except Project.DoesNotExist:
            pass

    return None


def authorize(f: ViewFunc) -> ViewFunc:
    @wraps(f)
    def wrapper(request: ApiRequest, *args: Any, **kwds: Any) -> HttpResponse:
        # For POST requests, we may need to look for the API key inside the
        # request body. Parse the body and put it in request.json
        # so views can avoid parsing it again.
        if request.method == "POST" and request.body:
            try:
                request.json = json.loads(request.body.decode())
            except ValueError:
                return error("could not parse request body")
            if not isinstance(request.json, dict):
                return error("json validation error: value is not an object")
        else:
            request.json = {}

        if "HTTP_X_API_KEY" in request.META:
            api_key = request.META["HTTP_X_API_KEY"]
        elif "api_key" in request.json:
            api_key = str(request.json["api_key"])
        else:
            api_key = ""

        if len(api_key) != 32:
            return error("missing api key", 401)

        project = lookup_project(api_key, require_rw=True)
        if project is None:
            return error("wrong api key", 401)

        request.project = project
        request.readonly = False
        request.v = _get_api_version(request)
        return f(request, *args, **kwds)

    return wrapper


def authorize_read(f: ViewFunc) -> ViewFunc:
    @wraps(f)
    def wrapper(request: ApiRequest, *args: Any, **kwds: Any) -> HttpResponse:
        if "HTTP_X_API_KEY" in request.META:
            api_key = request.META["HTTP_X_API_KEY"]
        else:
            api_key = ""

        if len(api_key) != 32:
            return error("missing api key", 401)

        project = lookup_project(api_key, require_rw=False)
        if project is None:
            return error("wrong api key", 401)

        request.project = project
        request.readonly = (
            api_key.startswith("hcr_") or api_key == request.project.api_key_readonly
        )
        request.v = _get_api_version(request)
        return f(request, *args, **kwds)

    return wrapper


def cors(*methods: str) -> Callable[[ViewFunc], ViewFunc]:
    methods_set = set(methods)
    methods_set.add("OPTIONS")
    methods_str = ", ".join(methods_set)

    def decorator(f: ViewFunc) -> ViewFunc:
        @wraps(f)
        def wrapper(request: HttpRequest, *args: Any, **kwds: Any) -> HttpResponse:
            if request.method == "OPTIONS":
                # Handle OPTIONS here
                response = HttpResponse(status=204)
            elif request.method in methods:
                response = f(request, *args, **kwds)
            else:
                response = HttpResponse(status=405)

            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Headers"] = "X-Api-Key"
            response["Access-Control-Allow-Methods"] = methods_str
            response["Access-Control-Max-Age"] = "600"
            return response

        return wrapper

    return decorator
