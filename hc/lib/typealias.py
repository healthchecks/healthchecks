from __future__ import annotations

from typing import Dict, List

JSONDict = Dict[str, "JSONValue"]
JSONList = List["JSONValue"]
JSONValue = JSONDict | JSONList | str | int | float | bool | None
