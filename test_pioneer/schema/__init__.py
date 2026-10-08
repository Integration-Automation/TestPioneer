"""The workflow contract: its vocabulary (``spec``) and its JSON Schema (``definition``)."""
from __future__ import annotations

from test_pioneer.schema.definition import SCHEMA_VERSION, build_schema
from test_pioneer.schema.spec import JsonSchema


def get_yaml_schema() -> JsonSchema:
    """Return the JSON Schema of a workflow file; the caller owns the returned dict."""
    return build_schema()


__all__ = ["SCHEMA_VERSION", "get_yaml_schema"]
