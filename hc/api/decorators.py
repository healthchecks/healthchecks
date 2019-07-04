import json
from functools import wraps

from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from hc.accounts.models import Project
from hc.lib.jsonschema import ValidationError, validate


def error(msg, status=400):
    return JsonResponse({"error": msg}, status=status)


def authorize(f):
    @wraps(f)
    def wrapper(request, *args, **kwds):
        if "HTTP_X_API_KEY" in request.META:
            api_key = request.META["HTTP_X_API_KEY"]
        else:
            api_key = str(request.json.get("api_key", ""))

        if len(api_key) != 32:
            return error("missing api key", 401)

        try:
            request.project = Project.objects.get(api_key=api_key)
        except Project.DoesNotExist:
            return error("wrong api key", 401)

        request.readonly = False
        return f(request, *args, **kwds)

    return wrapper


def authorize_read(f):
    @wraps(f)
    def wrapper(request, *args, **kwds):
        if "HTTP_X_API_KEY" in request.META:
            api_key = request.META["HTTP_X_API_KEY"]
        else:
            api_key = str(request.json.get("api_key", ""))

        if len(api_key) != 32:
            return error("missing api key", 401)

        write_key_match = Q(api_key=api_key)
        read_key_match = Q(api_key_readonly=api_key)
        try:
            request.project = Project.objects.get(write_key_match | read_key_match)
        except Project.DoesNotExist:
            return error("wrong api key", 401)

        request.readonly = api_key == request.project.api_key_readonly
        return f(request, *args, **kwds)

    return wrapper


def validate_json(schema=None):
    """ Parse request json and validate it against `schema`.

    Put the parsed result in `request.json`.
    If schema is None then only parse and don't validate.
    Supports  a limited subset of JSON schema spec.

    """

    def decorator(f):
        @wraps(f)
        def wrapper(request, *args, **kwds):
            if request.body:
                try:
                    request.json = json.loads(request.body.decode())
                except ValueError:
                    return error("could not parse request body")
            else:
                request.json = {}

            if schema:
                try:
                    validate(request.json, schema)
                except ValidationError as e:
                    return error("json validation error: %s" % e)

            return f(request, *args, **kwds)

        return wrapper

    return decorator


def cors(*methods):
    methods = set(methods)
    methods.add("OPTIONS")
    methods_str = ", ".join(methods)

    def decorator(f):
        @wraps(f)
        def wrapper(request, *args, **kwds):
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
