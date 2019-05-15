""" A minimal jsonschema validator.

Supports only a tiny subset of jsonschema.

"""

from croniter import croniter
from pytz import all_timezones


class ValidationError(Exception):
    pass


def validate(obj, schema, obj_name="value"):
    if schema.get("type") == "string":
        if not isinstance(obj, str):
            raise ValidationError("%s is not a string" % obj_name)
        if "minLength" in schema and len(obj) < schema["minLength"]:
            raise ValidationError("%s is too short" % obj_name)
        if "maxLength" in schema and len(obj) > schema["maxLength"]:
            raise ValidationError("%s is too long" % obj_name)
        if schema.get("format") == "cron":
            try:
                croniter(obj)
            except:
                raise ValidationError("%s is not a valid cron expression" % obj_name)
        if schema.get("format") == "timezone" and obj not in all_timezones:
            raise ValidationError("%s is not a valid timezone" % obj_name)

    elif schema.get("type") == "number":
        if not isinstance(obj, int):
            raise ValidationError("%s is not a number" % obj_name)
        if "minimum" in schema and obj < schema["minimum"]:
            raise ValidationError("%s is too small" % obj_name)
        if "maximum" in schema and obj > schema["maximum"]:
            raise ValidationError("%s is too large" % obj_name)

    elif schema.get("type") == "array":
        if not isinstance(obj, list):
            raise ValidationError("%s is not an array" % obj_name)

        for v in obj:
            validate(v, schema["items"], "an item in '%s'" % obj_name)

    elif schema.get("type") == "object":
        if not isinstance(obj, dict):
            raise ValidationError("%s is not an object" % obj_name)

        properties = schema.get("properties", {})
        for key, spec in properties.items():
            if key in obj:
                validate(obj[key], spec, obj_name=key)

        for key in schema.get("required", []):
            if key not in obj:
                raise ValidationError("key %s absent in %s" % (key, obj_name))

    if "enum" in schema:
        if obj not in schema["enum"]:
            raise ValidationError("%s has unexpected value" % obj_name)
