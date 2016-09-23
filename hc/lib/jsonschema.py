""" A minimal jsonschema validator.

Supports only a tiny subset of jsonschema.

"""

from six import string_types


class ValidationError(Exception):
    pass


def validate(obj, schema, obj_name="value"):
    if schema.get("type") == "string":
        if not isinstance(obj, string_types):
            raise ValidationError("%s is not a string" % obj_name)

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

        for key, spec in schema["properties"].items():
            if key in obj:
                validate(obj[key], spec, obj_name=key)

    if "enum" in schema:
        if obj not in schema["enum"]:
            raise ValidationError("%s has unexpected value" % obj_name)
