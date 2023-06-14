""" A minimal jsonschema validator.

Supports only a tiny subset of jsonschema.

"""

from __future__ import annotations

import re
from datetime import datetime

from cronsim import CronSim

from hc.lib.tz import all_timezones


class ValidationError(Exception):
    pass


def validate(obj, schema, obj_name="value"):
    if schema.get("type") == "string":
        if not isinstance(obj, str):
            raise ValidationError(f"{obj_name} is not a string")
        if "minLength" in schema and len(obj) < schema["minLength"]:
            raise ValidationError(f"{obj_name} is too short")
        if "maxLength" in schema and len(obj) > schema["maxLength"]:
            raise ValidationError(f"{obj_name} is too long")
        if "pattern" in schema and not re.match(schema["pattern"], obj):
            raise ValidationError(f"{obj_name} does not match pattern")
        if schema.get("format") == "cron":
            try:
                # Does it have 5 components?
                if len(obj.split()) != 5:
                    raise ValueError()

                # Does cronsim accept the schedule?
                it = CronSim(obj, datetime(2000, 1, 1))
                # Can it calculate the next datetime?
                next(it)
            except:
                raise ValidationError(f"{obj_name} is not a valid cron expression")
        if schema.get("format") == "timezone" and obj not in all_timezones:
            raise ValidationError(f"{obj_name} is not a valid timezone")

    elif schema.get("type") == "number":
        if not isinstance(obj, int):
            raise ValidationError(f"{obj_name} is not a number")
        if "minimum" in schema and obj < schema["minimum"]:
            raise ValidationError(f"{obj_name} is too small")
        if "maximum" in schema and obj > schema["maximum"]:
            raise ValidationError(f"{obj_name} is too large")

    elif schema.get("type") == "boolean":
        if not isinstance(obj, bool):
            raise ValidationError(f"{obj_name} is not a boolean")

    elif schema.get("type") == "array":
        if not isinstance(obj, list):
            raise ValidationError(f"{obj_name} is not an array")

        for v in obj:
            validate(v, schema["items"], f"an item in '{obj_name}'")

    elif schema.get("type") == "object":
        if not isinstance(obj, dict):
            raise ValidationError(f"{obj_name} is not an object")

        properties = schema.get("properties", {})
        for key, spec in properties.items():
            if key in obj:
                validate(obj[key], spec, obj_name=key)

        for key in schema.get("required", []):
            if key not in obj:
                raise ValidationError(f"key {key} absent in {obj_name}")

    if "enum" in schema:
        if obj not in schema["enum"]:
            raise ValidationError(f"{obj_name} has unexpected value")
