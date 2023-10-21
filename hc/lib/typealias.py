from __future__ import annotations

from typing import Callable

from django.http import HttpResponse

JSONDict = dict[str, "JSONValue"]
JSONList = list["JSONValue"]
JSONValue = JSONDict | JSONList | str | int | float | bool | None


ViewFunc = Callable[..., HttpResponse]
