from django.test import TestCase

from hc.lib.jsonschema import ValidationError, validate


class JsonSchemaTestCase(TestCase):
    def test_it_validates_strings(self):
        validate("foo", {"type": "string"})

    def test_it_checks_string_type(self):
        with self.assertRaises(ValidationError):
            validate(123, {"type": "string"})

    def test_it_checks_string_min_length(self):
        with self.assertRaises(ValidationError):
            validate("abcd", {"type": "string", "minLength": 5})

    def test_it_checks_string_length(self):
        with self.assertRaises(ValidationError):
            validate("abcd", {"type": "string", "maxLength": 3})

    def test_it_validates_numbers(self):
        validate(123, {"type": "number", "minimum": 0, "maximum": 1000})

    def test_it_checks_int_type(self):
        with self.assertRaises(ValidationError):
            validate("foo", {"type": "number"})

    def test_it_checks_min_value(self):
        with self.assertRaises(ValidationError):
            validate(5, {"type": "number", "minimum": 10})

    def test_it_checks_max_value(self):
        with self.assertRaises(ValidationError):
            validate(5, {"type": "number", "maximum": 0})

    def test_it_validates_objects(self):
        validate(
            {"foo": "bar"},
            {"type": "object", "properties": {"foo": {"type": "string"}}},
        )

    def test_it_checks_dict_type(self):
        with self.assertRaises(ValidationError):
            validate("not-object", {"type": "object"})

    def test_it_validates_objects_properties(self):
        with self.assertRaises(ValidationError):
            validate(
                {"foo": "bar"},
                {"type": "object", "properties": {"foo": {"type": "number"}}},
            )

    def test_it_handles_required_properties(self):
        with self.assertRaises(ValidationError):
            validate({"foo": "bar"}, {"type": "object", "required": ["baz"]})

    def test_it_validates_arrays(self):
        validate(["foo", "bar"], {"type": "array", "items": {"type": "string"}})

    def test_it_validates_array_type(self):
        with self.assertRaises(ValidationError):
            validate("not-an-array", {"type": "array", "items": {"type": "string"}})

    def test_it_validates_array_elements(self):
        with self.assertRaises(ValidationError):
            validate(["foo", "bar"], {"type": "array", "items": {"type": "number"}})

    def test_it_validates_enum(self):
        validate("foo", {"enum": ["foo", "bar"]})

    def test_it_rejects_a_value_not_in_enum(self):
        with self.assertRaises(ValidationError):
            validate("baz", {"enum": ["foo", "bar"]})

    def test_it_checks_cron_format(self):
        with self.assertRaises(ValidationError):
            validate("x * * * *", {"type": "string", "format": "cron"})

    def test_it_checks_timezone_format(self):
        with self.assertRaises(ValidationError):
            validate("X/Y", {"type": "string", "format": "timezone"})
