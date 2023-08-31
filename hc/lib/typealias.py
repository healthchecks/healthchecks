from __future__ import annotations

from typing import Dict, List, Union

JSONDict = Dict[str, "JSONValue"]
JSONList = List["JSONValue"]
JSONValue = Union[JSONDict, JSONList, str, int, float, bool, None]
