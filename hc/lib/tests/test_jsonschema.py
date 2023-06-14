from __future__ import annotations

from unittest import TestCase

from hc.lib.jsonschema import ValidationError, validate


class JsonSchemaTestCase(TestCase):
    def test_it_validates_strings(self):
        validate("foo", {"type": "string"})

    def test_it_checks_string_type(self):
        validate("123", {"type": "string"})
        with self.assertRaises(ValidationError):
            validate(123, {"type": "string"})

    def test_it_checks_string_min_length(self):
        validate("abcde", {"type": "string", "minLength": 5})
        with self.assertRaises(ValidationError):
            validate("abcd", {"type": "string", "minLength": 5})

    def test_it_checks_string_length(self):
        validate("abc", {"type": "string", "maxLength": 3})
        with self.assertRaises(ValidationError):
            validate("abcd", {"type": "string", "maxLength": 3})

    def test_it_checks_string_pattern(self):
        validate("abcd", {"type": "string", "pattern": "^[a-z]*$"})
        with self.assertRaises(ValidationError):
            validate("ab1cd", {"type": "string", "pattern": "^[a-z]*$"})

    def test_it_validates_numbers(self):
        validate(123, {"type": "number", "minimum": 0, "maximum": 1000})

    def test_it_checks_int_type(self):
        with self.assertRaises(ValidationError):
            validate("foo", {"type": "number"})

    def test_it_checks_min_value(self):
        validate(10, {"type": "number", "minimum": 10})
        with self.assertRaises(ValidationError):
            validate(5, {"type": "number", "minimum": 10})

    def test_it_checks_max_value(self):
        validate(0, {"type": "number", "maximum": 0})
        with self.assertRaises(ValidationError):
            validate(5, {"type": "number", "maximum": 0})

    def test_it_validates_objects(self):
        validate(
            {"foo": "bar"},
            {"type": "object", "properties": {"foo": {"type": "string"}}},
        )

    def test_it_checks_dict_type(self):
        validate({}, {"type": "object"})
        with self.assertRaises(ValidationError):
            validate("not-object", {"type": "object"})

    def test_it_validates_objects_properties(self):
        validate(
            {"foo": 123},
            {"type": "object", "properties": {"foo": {"type": "number"}}},
        )

        with self.assertRaises(ValidationError):
            validate(
                {"foo": "bar"},
                {"type": "object", "properties": {"foo": {"type": "number"}}},
            )

    def test_it_handles_required_properties(self):
        validate({"baz": True}, {"type": "object", "required": ["baz"]})
        with self.assertRaises(ValidationError):
            validate({"foo": "bar"}, {"type": "object", "required": ["baz"]})

    def test_it_validates_arrays(self):
        validate(["foo", "bar"], {"type": "array", "items": {"type": "string"}})

    def test_it_validates_array_type(self):
        validate([], {"type": "array", "items": {"type": "string"}})
        with self.assertRaises(ValidationError):
            validate("not-an-array", {"type": "array", "items": {"type": "string"}})

    def test_it_validates_array_elements(self):
        validate([1, 2], {"type": "array", "items": {"type": "number"}})
        with self.assertRaises(ValidationError):
            validate(["foo", "bar"], {"type": "array", "items": {"type": "number"}})

    def test_it_validates_enum(self):
        validate("foo", {"enum": ["foo", "bar"]})

    def test_it_rejects_a_value_not_in_enum(self):
        validate("foo", {"enum": ["foo", "bar"]})
        with self.assertRaises(ValidationError):
            validate("baz", {"enum": ["foo", "bar"]})

    def test_it_checks_cron_format(self):
        validate("* * * * *", {"type": "string", "format": "cron"})

        samples = ["x * * * *", "0 0 31 2 *", "* * * * * *", "0 0 */100 * MON#2"]
        for sample in samples:
            with self.assertRaises(ValidationError):
                validate(sample, {"type": "string", "format": "cron"})

    def test_it_checks_timezone_format(self):
        validate("Europe/Riga", {"type": "string", "format": "timezone"})
        with self.assertRaises(ValidationError):
            validate("X/Y", {"type": "string", "format": "timezone"})

    def test_it_checks_boolean_type(self):
        validate(True, {"type": "boolean"})
        with self.assertRaises(ValidationError):
            validate(123, {"type": "boolean"})
