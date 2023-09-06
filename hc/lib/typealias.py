from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict, List, Union

from django.contrib.auth.models import User
from django.http import HttpRequest, HttpResponse

if TYPE_CHECKING:
    # Import Profile only when type-checking to avoid import loops
    from hc.accounts.models import Profile

JSONDict = Dict[str, "JSONValue"]
JSONList = List["JSONValue"]
JSONValue = Union[JSONDict, JSONList, str, int, float, bool, None]


ViewFunc = Callable[..., HttpResponse]


class AuthenticatedHttpRequest(HttpRequest):
    user: User
    profile: Profile
