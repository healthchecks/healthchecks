import uuid
from functools import wraps

from django.http import HttpResponseBadRequest


def uuid_or_400(f):
    @wraps(f)
    def wrapper(request, *args, **kwds):
        try:
            uuid.UUID(args[0])
        except ValueError:
            return HttpResponseBadRequest()

        return f(request, *args, **kwds)
    return wrapper
