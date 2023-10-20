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

        try:
            request.project = Project.objects.get(api_key=api_key)
        except Project.DoesNotExist:
            return error("wrong api key", 401)

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

        write_key_match = Q(api_key=api_key)
        read_key_match = Q(api_key_readonly=api_key)
        try:
            request.project = Project.objects.get(write_key_match | read_key_match)
        except Project.DoesNotExist:
            return error("wrong api key", 401)

        request.readonly = api_key == request.project.api_key_readonly
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
