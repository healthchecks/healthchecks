from __future__ import annotations

from django.contrib.auth.models import User
from django.http import HttpRequest

from hc.accounts.models import Profile


class AuthenticatedHttpRequest(HttpRequest):
    user: User
    profile: Profile
