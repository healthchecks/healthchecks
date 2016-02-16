import json
import uuid
from functools import wraps

from django.contrib.auth.models import User
from django.http import HttpResponseBadRequest, JsonResponse


def uuid_or_400(f):
    @wraps(f)
    def wrapper(request, *args, **kwds):
        try:
            uuid.UUID(args[0])
        except ValueError:
            return HttpResponseBadRequest()

        return f(request, *args, **kwds)
    return wrapper


def make_error(msg):
    return JsonResponse({"error": msg}, status=400)


def check_api_key(f):
    @wraps(f)
    def wrapper(request, *args, **kwds):
        try:
            data = json.loads(request.body.decode("utf-8"))
        except ValueError:
            return make_error("could not parse request body")

        api_key = str(data.get("api_key", ""))
        if api_key == "":
            return make_error("wrong api_key")

        try:
            user = User.objects.get(profile__api_key=api_key)
        except User.DoesNotExist:
            return make_error("wrong api_key")

        request.json = data
        request.user = user
        return f(request, *args, **kwds)

    return wrapper


def validate_json(schema):
    """ Validate request.json contents against `schema`.

    Supports a tiny subset of JSON schema spec.

    """

    def decorator(f):
        @wraps(f)
        def wrapper(request, *args, **kwds):
            for key, spec in schema["properties"].items():
                if key not in request.json:
                    continue

                value = request.json[key]
                if spec["type"] == "string":
                    if not isinstance(value, str):
                        return make_error("%s is not a string" % key)
                elif spec["type"] == "number":
                    if not isinstance(value, int):
                        return make_error("%s is not a number" % key)
                    if "minimum" in spec and value < spec["minimum"]:
                        return make_error("%s is too small" % key)
                    if "maximum" in spec and value > spec["maximum"]:
                        return make_error("%s is too large" % key)

            return f(request, *args, **kwds)
        return wrapper
    return decorator
