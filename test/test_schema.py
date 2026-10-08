"""Tests for test_pioneer.schema: the workflow vocabulary and its JSON Schema."""
import json
from pathlib import Path

import pytest

from test_pioneer import get_yaml_schema
from test_pioneer.executor.pioneer_executor import _STEP_HANDLERS
from test_pioneer.executor.run.parallel_run import _BASE_RUNNER_COMMANDS
from test_pioneer.runner.registry import OPTIONAL_RUNNERS, RUNNER_NAMES, RUNNER_PACKAGES
from test_pioneer.schema import SCHEMA_VERSION
from test_pioneer.schema.spec import ACTION_KEYS, ACTIONS, STEP_FIELDS, STEP_KEYS
from test_pioneer.validation.schema_validator import ANNOTATION_KEYWORDS, CONSTRAINT_KEYWORDS

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLISHED_SCHEMA = REPO_ROOT / "schema" / "testpioneer.schema.json"
# Keywords whose value maps names to schemas, not keywords to values.
_NAME_MAPS = ("properties", "$defs")


def _keywords(schema: dict) -> set:
    """Collect every keyword used anywhere in a schema."""
    found = set(schema)
    for key, value in schema.items():
        if key in _NAME_MAPS:
            for item in value.values():
                found |= _keywords(item)
        elif isinstance(value, dict):
            found |= _keywords(value)
    return found


def _types(schema: dict) -> list:
    """Collect every ``type`` value used anywhere in a schema."""
    found = [schema["type"]] if "type" in schema else []
    for key, value in schema.items():
        children = value.values() if key in _NAME_MAPS else [value]
        for item in children:
            if isinstance(item, dict):
                found += _types(item)
    return found


class TestPublishedSchema:
    def test_checked_in_file_matches_the_built_schema(self):
        # Regenerate with: python -m test_pioneer schema > schema/testpioneer.schema.json
        assert json.loads(PUBLISHED_SCHEMA.read_text(encoding="utf-8")) == get_yaml_schema()

    def test_schema_is_versioned(self):
        schema = get_yaml_schema()
        assert schema["version"] == SCHEMA_VERSION
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["$id"].endswith("/schema/testpioneer.schema.json")

    def test_each_call_returns_an_independent_copy(self):
        first = get_yaml_schema()
        first["$defs"]["runner"]["enum"].append("other-runner")
        assert get_yaml_schema()["$defs"]["runner"]["enum"] == list(RUNNER_NAMES)


class TestSchemaContent:
    def test_top_level_keys(self):
        schema = get_yaml_schema()
        assert set(schema["properties"]) == {
            "pioneer_log", "recording_path", "artifacts_path", "keep_artifacts", "report_path",
            "report_formats", "jobs"}
        assert schema["required"] == ["jobs"]
        assert schema["properties"]["jobs"]["required"] == ["steps"]

    def test_step_lists_every_action_and_field(self):
        step = get_yaml_schema()["$defs"]["step"]
        assert step["required"] == ["name"]
        assert tuple(step["properties"]) == STEP_KEYS

    def test_runner_enum_is_the_registry(self):
        assert get_yaml_schema()["$defs"]["runner"]["enum"] == [
            "gui-runner", "web-runner", "api-runner", "load-runner", "file-runner"]

    def test_parallel_run_pairs_runners_with_scripts(self):
        block = get_yaml_schema()["$defs"]["parallel_run"]
        assert block["required"] == ["runners", "scripts"]
        assert block["properties"]["runners"]["items"] == {"$ref": "#/$defs/runner"}
        assert block["properties"]["artifacts"]["items"]["items"] == {"type": "string", "minLength": 1}

    def test_report_formats_are_an_enumerated_list(self):
        formats = get_yaml_schema()["properties"]["report_formats"]
        assert formats["items"]["enum"] == ["json", "html", "junit"]

    def test_every_field_belongs_to_an_action(self):
        used = {name for action in ACTIONS for name in action.fields}
        assert used == set(STEP_FIELDS)


class TestBuiltInValidatorCoversTheSchema:
    def test_schema_uses_only_keywords_the_validator_knows(self):
        assert _keywords(get_yaml_schema()) <= CONSTRAINT_KEYWORDS | ANNOTATION_KEYWORDS

    def test_every_type_is_a_single_json_type(self):
        allowed = {"object", "array", "string", "integer", "number", "boolean", "null"}
        assert set(_types(get_yaml_schema())) <= allowed


class TestSpecMatchesTheExecutor:
    def test_actions_are_the_executor_handlers_in_dispatch_order(self):
        assert tuple(_STEP_HANDLERS) == ACTION_KEYS

    def test_parallel_run_starts_every_core_runner_package(self):
        expected = {name: package for name, package in RUNNER_PACKAGES.items() if name not in OPTIONAL_RUNNERS}
        assert _BASE_RUNNER_COMMANDS == expected
        assert set(OPTIONAL_RUNNERS) == {"gui-runner"}


def test_schema_is_valid_for_the_reference_implementation():
    """With ``jsonschema`` installed, the schema passes the draft 2020-12 meta-schema."""
    jsonschema = pytest.importorskip("jsonschema")  # reason: not a dependency of test_pioneer
    jsonschema.Draft202012Validator.check_schema(get_yaml_schema())
