from hc.accounts.models import Profile
from django.contrib.auth.middleware import RemoteUserMiddleware
from django.contrib.auth.backends import RemoteUserBackend
from django.conf import settings


class TeamAccessMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        request.profile = Profile.objects.for_user(request.user)
        return self.get_response(request)

from django.contrib.auth.middleware import RemoteUserMiddleware

class CustomHeaderMiddleware(RemoteUserMiddleware):
    header = settings.REMOTE_USER_HEADER