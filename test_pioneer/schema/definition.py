"""Build the versioned JSON Schema of a TestPioneer workflow.

``schema/testpioneer.schema.json`` in the repository is this schema written to disk; a test keeps
the two identical. Regenerate the file with ``python -m test_pioneer schema > <path>``.
"""
from __future__ import annotations

import copy

from test_pioneer.runner.registry import RUNNER_NAMES
from test_pioneer.schema.spec import ACTIONS, STEP_FIELDS, TOP_LEVEL_FIELDS, JsonSchema, artifact_patterns

# Bump the minor part for a backward-compatible addition, the major part when a workflow that
# used to validate no longer does.
SCHEMA_VERSION = "1.0.0"
SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_ID = ("https://raw.githubusercontent.com/Integration-Automation/TestPioneer/main/"
             "schema/testpioneer.schema.json")


def _step_schema() -> JsonSchema:
    """Schema of one entry of ``jobs.steps``."""
    properties: JsonSchema = {
        "name": {
            "type": "string",
            "minLength": 1,
            "description": "Unique step name. close_program refers to an open_program step by it.",
        },
    }
    for action in ACTIONS:
        properties[action.key] = dict(action.value)
    for key, schema in STEP_FIELDS.items():
        properties[key] = dict(schema)
    return {
        "type": "object",
        "description": "One step: a name plus exactly one action key and that action's fields.",
        "required": ["name"],
        "properties": properties,
    }


def _parallel_run_schema() -> JsonSchema:
    """Schema of the value of a ``parallel_run`` step."""
    return {
        "type": "object",
        "description": "Scripts started together as sub-processes, one runner per script.",
        "required": ["runners", "scripts"],
        "properties": {
            "runners": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/$defs/runner"},
                "description": "Runner of each script. Same length as scripts.",
            },
            "scripts": {
                "type": "array",
                "minItems": 1,
                "items": {"type": "string", "minLength": 1},
                "description": "JSON action file of each runner. Same length as runners.",
            },
            "executor_path": {
                "type": "string",
                "description": "Python executable that starts the runners. Defaults to this one.",
            },
            "artifacts": {
                "type": "array",
                "items": artifact_patterns("Files or folders written by the runner at this position."),
                "description": "What each runner writes, one list of patterns per script. Same length as scripts.",
            },
        },
    }


def build_schema() -> JsonSchema:
    """Return a new copy of the workflow JSON Schema (draft 2020-12)."""
    properties: JsonSchema = {key: dict(schema) for key, schema in TOP_LEVEL_FIELDS.items()}
    properties["jobs"] = {
        "type": "object",
        "description": "Container of the steps list.",
        "required": ["steps"],
        "properties": {
            "steps": {
                "type": "array",
                "minItems": 1,
                "items": {"$ref": "#/$defs/step"},
                "description": "Steps, run in order. A failed step stops the ones after it.",
            },
        },
    }
    schema: JsonSchema = {
        "$schema": SCHEMA_DRAFT,
        "$id": SCHEMA_ID,
        "title": "TestPioneer workflow",
        "description": "A YAML workflow executed by test_pioneer.",
        "version": SCHEMA_VERSION,
        "type": "object",
        "required": ["jobs"],
        "properties": properties,
        "$defs": {
            "runner": {
                "type": "string",
                "enum": list(RUNNER_NAMES),
                "description": "Runner that executes a JSON action file.",
            },
            "step": _step_schema(),
            "parallel_run": _parallel_run_schema(),
        },
    }
    return copy.deepcopy(schema)
