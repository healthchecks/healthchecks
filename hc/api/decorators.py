import json
import re
from functools import wraps

from django.contrib.auth.models import User
from django.http import (HttpResponseBadRequest, HttpResponseForbidden,
                         JsonResponse)
from hc.lib.jsonschema import ValidationError, validate

RE_UUID = re.compile("^[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-4[a-fA-F0-9]{3}-[8|9|aA|bB][a-fA-F0-9]{3}-[a-fA-F0-9]{12}$")


def uuid_or_400(f):
    @wraps(f)
    def wrapper(request, *args, **kwds):
        if not RE_UUID.match(args[0]):
            return HttpResponseBadRequest()

        return f(request, *args, **kwds)
    return wrapper


def make_error(msg):
    return JsonResponse({"error": msg}, status=400)


def check_api_key(f):
    @wraps(f)
    def wrapper(request, *args, **kwds):
        request.json = {}
        if request.body:
            try:
                request.json = json.loads(request.body.decode("utf-8"))
            except ValueError:
                return make_error("could not parse request body")

        if "HTTP_X_API_KEY" in request.META:
            api_key = request.META["HTTP_X_API_KEY"]
        else:
            api_key = request.json.get("api_key", "")

        if api_key == "":
            return make_error("wrong api_key")

        try:
            request.user = User.objects.get(profile__api_key=api_key)
        except User.DoesNotExist:
            return HttpResponseForbidden()

        return f(request, *args, **kwds)

    return wrapper


def validate_json(schema):
    """ Validate request.json contents against `schema`.

    Supports a tiny subset of JSON schema spec.

    """

    def decorator(f):
        @wraps(f)
        def wrapper(request, *args, **kwds):
            try:
                validate(request.json, schema)
            except ValidationError as e:
                return make_error("json validation error: %s" % e)

            return f(request, *args, **kwds)
        return wrapper
    return decorator
