from __future__ import annotations

from typing import Callable

from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User
from django.core.exceptions import MiddlewareNotUsed
from django.http import HttpRequest, HttpResponse

from hc.accounts.models import Profile

MiddlewareFunc = Callable[[HttpRequest], HttpResponse]


class TeamAccessMiddleware(object):
    def __init__(self, get_response: MiddlewareFunc) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_authenticated:
            return self.get_response(request)

        setattr(request, "profile", Profile.objects.for_user(request.user))
        return self.get_response(request)


class CustomHeaderMiddleware(object):
    """
    Middleware for utilizing Web-server-provided authentication.

    If request.user is not authenticated, then this middleware:
    - looks for an email address in request.META[settings.REMOTE_USER_HEADER]
    - looks up and automatically logs in the user with a matching email

    """

    def __init__(self, get_response: MiddlewareFunc) -> None:
        if not settings.REMOTE_USER_HEADER:
            raise MiddlewareNotUsed()

        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        assert settings.REMOTE_USER_HEADER
        # Make sure AuthenticationMiddleware is installed
        assert hasattr(request, "user")

        email = request.META.get(settings.REMOTE_USER_HEADER)
        if not email:
            # If specified header doesn't exist or is empty then log out any
            # authenticated user and return
            if request.user.is_authenticated:
                auth.logout(request)
            return self.get_response(request)

        # If the user is already authenticated and that user is the user we are
        # getting passed in the headers, then the correct user is already
        # persisted in the session and we don't need to continue.
        if request.user.is_authenticated:
            if request.user.email == email:
                return self.get_response(request)
            else:
                # An authenticated user is associated with the request, but
                # it does not match the authorized user in the header.
                auth.logout(request)

        # We are seeing this user for the first time in this session, attempt
        # to authenticate the user.
        if user := auth.authenticate(request, remote_user_email=email):
            assert isinstance(user, User)
            # User is valid.  Set request.user and persist user in the session
            # by logging the user in.
            request.user = user
            auth.login(request, user)

        return self.get_response(request)
