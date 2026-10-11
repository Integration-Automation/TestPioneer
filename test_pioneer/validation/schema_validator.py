"""Check parsed workflow data against the workflow JSON Schema.

Only the keywords that schema uses are implemented (``CONSTRAINT_KEYWORDS``). A test keeps the
schema inside this subset, so no constraint is skipped silently, and TestPioneer needs no
third-party JSON Schema package to validate a workflow.
"""
from __future__ import annotations

import difflib
from collections.abc import Iterator, Mapping

from test_pioneer.models.diagnostic import Diagnostic, Severity, YamlPath
from test_pioneer.schema import get_yaml_schema
from test_pioneer.validation.yaml_loader import YamlDocument

CONSTRAINT_KEYWORDS: frozenset[str] = frozenset({
    "$ref", "type", "enum", "required", "properties", "items", "minItems", "minLength", "minimum",
})
ANNOTATION_KEYWORDS: frozenset[str] = frozenset({
    "$schema", "$id", "$defs", "title", "description", "version",
})

_DEFINITIONS = "#/$defs/"
_MAX_SHOWN = 40
# bool comes before int: in Python a bool is an int, in JSON Schema it is not.
_JSON_TYPES: tuple[tuple[type, str], ...] = (
    (bool, "boolean"), (int, "integer"), (float, "number"), (str, "string"),
    (list, "array"), (dict, "object"),
)
_TYPE_LABELS: Mapping[str, str] = {
    "object": "a mapping", "array": "a list", "string": "a string", "integer": "an integer",
    "number": "a number", "boolean": "true or false", "null": "null",
}


def json_type(value: object) -> str:
    """Name the JSON type of a parsed YAML value; other types are named by their class."""
    if value is None:
        return "null"
    for python_type, name in _JSON_TYPES:
        if isinstance(value, python_type):
            return name
    return type(value).__name__


def suggestion(word: str, candidates: list[str]) -> str:
    """Return `` Did you mean 'x'?`` for the closest candidate, or an empty string."""
    close = difflib.get_close_matches(word, candidates, n=1)
    return f" Did you mean '{close[0]}'?" if close else ""


def _label(type_name: str) -> str:
    return _TYPE_LABELS.get(type_name, type_name)


def _enum_message(value: object, allowed: list[object]) -> str:
    shown = repr(value)
    if len(shown) > _MAX_SHOWN:
        shown = shown[:_MAX_SHOWN] + "..."
    names = [str(item) for item in allowed]
    return f"{shown} is not one of: {', '.join(names)}.{suggestion(str(value), names)}"


class _SchemaChecker:  # pylint: disable=too-few-public-methods  # one entry point over shared state
    """Walks data and schema together, yielding one diagnostic per violated constraint."""

    def __init__(self, schema: Mapping[str, object], document: YamlDocument) -> None:
        self._document = document
        definitions = schema.get("$defs")
        self._definitions: dict[str, Mapping[str, object]] = {
            f"{_DEFINITIONS}{name}": target
            for name, target in (definitions.items() if isinstance(definitions, dict) else ())
            if isinstance(target, dict)
        }

    def check(self, value: object, schema: Mapping[str, object], path: YamlPath) -> Iterator[Diagnostic]:
        """Yield the problems of ``value`` and of everything below it."""
        schema = self._resolve(schema)
        expected = schema.get("type")
        actual = json_type(value)
        if isinstance(expected, str) and actual != expected and (expected, actual) != ("number", "integer"):
            yield self._error("schema-type", f"expected {_label(expected)}, got {_label(actual)}", path)
            return
        yield from self._check_scalar(value, schema, path)
        if isinstance(value, dict):
            yield from self._check_mapping(value, schema, path)
        elif isinstance(value, list):
            yield from self._check_list(value, schema, path)

    def _resolve(self, schema: Mapping[str, object]) -> Mapping[str, object]:
        reference = schema.get("$ref")
        if not isinstance(reference, str):
            return schema
        target = self._definitions.get(reference)
        if target is None:
            raise ValueError(f"unsupported schema reference: {reference}")
        return target

    def _error(self, code: str, message: str, path: YamlPath, on_key: bool = False) -> Diagnostic:
        line, column = self._document.position(path, on_key)
        return Diagnostic(Severity.ERROR, code, message, path, line, column, "schema")

    def _check_scalar(self, value: object, schema: Mapping[str, object], path: YamlPath) -> Iterator[Diagnostic]:
        allowed = schema.get("enum")
        if isinstance(allowed, list) and value not in allowed:
            yield self._error("schema-enum", _enum_message(value, allowed), path)
        min_length = schema.get("minLength")
        if isinstance(value, str) and isinstance(min_length, int) and len(value) < min_length:
            yield self._error("schema-min-length", "must not be empty", path)
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and isinstance(value, (int, float)) \
                and not isinstance(value, bool) and value < minimum:
            yield self._error("schema-minimum", f"must be {minimum} or more, got {value}", path)

    def _check_mapping(self, value: dict[object, object], schema: Mapping[str, object],
                       path: YamlPath) -> Iterator[Diagnostic]:
        required = schema.get("required")
        for key in required if isinstance(required, list) else ():
            if key not in value:
                yield self._error("schema-required", f"missing required key '{key}'", path, on_key=True)
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            return
        for key, item in value.items():
            item_schema = properties.get(key)
            if isinstance(key, str) and isinstance(item_schema, dict):
                yield from self.check(item, item_schema, path + (key,))

    def _check_list(self, value: list[object], schema: Mapping[str, object],
                    path: YamlPath) -> Iterator[Diagnostic]:
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            yield self._error("schema-min-items", f"needs at least {min_items} item(s), got {len(value)}", path)
        item_schema = schema.get("items")
        if not isinstance(item_schema, dict):
            return
        for index, item in enumerate(value):
            yield from self.check(item, item_schema, path + (index,))


def check_schema(document: YamlDocument) -> list[Diagnostic]:
    """Return the schema violations of a parsed workflow, each located in its text."""
    schema = get_yaml_schema()
    return list(_SchemaChecker(schema, document).check(document.data, schema, ()))
