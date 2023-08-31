from __future__ import annotations

from typing import Dict, List, TypeAlias

JSONDict: TypeAlias = Dict[str, "JSONValue"]
JSONList: TypeAlias = List["JSONValue"]
JSONValue: TypeAlias = JSONDict | JSONList | str | int | float | bool | None
