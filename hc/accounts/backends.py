from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest

from hc.accounts.models import Profile
from hc.accounts.views import _make_user


class BasicBackend(object):
    def get_user(self, user_id: int) -> User | None:
        try:
            q = User.objects.select_related("profile")

            return q.get(pk=user_id)
        except User.DoesNotExist:
            return None


# Authenticate against the token in user's profile.
class ProfileBackend(BasicBackend):
    def authenticate(
        self,
        request: HttpRequest,
        username: str | None = None,
        token: str | None = None,
    ) -> User | None:
        if not token:
            return None

        try:
            profiles = Profile.objects.select_related("user")
            profile = profiles.get(user__username=username)
        except Profile.DoesNotExist:
            return None

        if not profile.check_token(token):
            return None

        return profile.user


class EmailBackend(BasicBackend):
    def authenticate(
        self,
        request: HttpRequest,
        username: str | None = None,
        password: str | None = None,
    ) -> User | None:
        if not password:
            return None

        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None

        if not user.check_password(password):
            return None

        return user


class CustomHeaderBackend(BasicBackend):
    """
    This backend works in conjunction with the ``CustomHeaderMiddleware``,
    and is used when the server is handling authentication outside of Django.

    """

    def authenticate(
        self, request: HttpRequest, remote_user_email: str | None = None
    ) -> User | None:
        """
        The email address passed as remote_user_email is considered trusted.
        Return the User object with the given email address. Create a new User
        if it does not exist.

        """

        # This backend should only be used when header-based authentication is enabled
        assert settings.REMOTE_USER_HEADER
        # remote_user_email should have a value
        assert remote_user_email

        try:
            user = User.objects.get(email=remote_user_email)
        except User.DoesNotExist:
            user = _make_user(remote_user_email)

        return user
