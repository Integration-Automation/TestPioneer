"""Tests for test_pioneer.validation.schema_validator, through ``validate_yaml``."""
import itertools

import pytest
import yaml

from test_pioneer import get_yaml_schema, validate_yaml
from test_pioneer.validation.schema_validator import _SchemaChecker, json_type, suggestion
from test_pioneer.validation.yaml_loader import load_yaml

VALID = """\
pioneer_log: "test_pioneer.log"
recording_path: "test_video"
artifacts_path: "build/artifacts"
keep_artifacts: always
report_path: "build/report"
report_formats: [json, html, junit]
jobs:
  steps:
    - name: run_api_test
      run: tests/api_test.json
      with: api-runner
      artifacts: ["reports/api_*.json", "screenshots"]
    - name: wait_for_service
      wait: 5
    - name: open_docs
      open_url: https://example.com
      url_open_method: open_new_tab
    - name: launch_app
      open_program: path/to/program
      redirect_stdout: output.log
      redirect_stderr: errors.log
    - name: close_launched_app
      close_program: launch_app
    - name: parallel_tests
      parallel_run:
        runners: ["web-runner", "api-runner"]
        scripts: ["./tests/web.json", "./tests/api.json"]
        executor_path: /usr/bin/python3
        artifacts: [["reports/web_*.json"], []]
    - name: run_all_in_folder
      run_folder: tests/regression/
      with: web-runner
    - name: download_asset
      download_file: https://example.com/asset.zip
      file_path: ./downloads/asset.zip
    - name: extract_asset
      unzip_zipfile: true
      zip_file_path: ./downloads/asset.zip
      extract_path: ./assets/
      password: secret
"""


def _step(body: str) -> str:
    """Wrap step lines (already indented by six spaces) in a one-step workflow."""
    return "jobs:\n  steps:\n    - name: only\n" + body


def _codes(text: str) -> list:
    return [item.code for item in validate_yaml(text, "String").diagnostics]


class TestValidWorkflows:
    def test_documented_full_example_has_no_problem(self):
        result = validate_yaml(VALID, "String")
        assert result.diagnostics == ()
        assert result.ok is True

    def test_file_input_reports_its_source(self, tmp_path):
        path = tmp_path / "flow.yml"
        path.write_text(VALID, encoding="utf-8")
        result = validate_yaml(str(path))
        assert result.ok is True
        assert result.source == str(path)

    def test_unknown_keys_are_not_a_schema_matter(self):
        assert _codes("extra: 1\njobs:\n  steps:\n    - name: a\n      wait: 1\n      note: hi\n") == []


class TestStructure:
    def test_empty_document(self):
        result = validate_yaml("", "String")
        assert [(item.code, item.message) for item in result.diagnostics] == [
            ("schema-type", "expected a mapping, got null")]

    def test_document_that_is_a_list(self):
        assert _codes("- a\n- b\n") == ["schema-type"]

    def test_missing_jobs(self):
        (problem,) = validate_yaml("pioneer_log: a.log\n", "String").diagnostics
        assert (problem.code, problem.message, problem.path) == (
            "schema-required", "missing required key 'jobs'", ())

    def test_jobs_that_is_not_a_mapping(self):
        (problem,) = validate_yaml("jobs: not_a_dict\n", "String").diagnostics
        assert (problem.code, problem.path, problem.line, problem.column) == ("schema-type", ("jobs",), 1, 7)

    def test_missing_steps_points_at_the_jobs_key(self):
        (problem,) = validate_yaml("jobs:\n  other: 1\n", "String").diagnostics
        assert (problem.code, problem.message) == ("schema-required", "missing required key 'steps'")
        assert (problem.line, problem.column) == (1, 1)

    def test_steps_without_a_value(self):
        (problem,) = validate_yaml("jobs:\n  steps:\n", "String").diagnostics
        assert (problem.code, problem.message) == ("schema-type", "expected a list, got null")

    def test_empty_steps_list(self):
        assert _codes("jobs:\n  steps: []\n") == ["schema-min-items"]

    def test_step_that_is_not_a_mapping(self):
        (problem,) = validate_yaml("jobs:\n  steps:\n    - just text\n", "String").diagnostics
        assert (problem.code, problem.path, problem.line) == ("schema-type", ("jobs", "steps", 0), 3)

    def test_step_without_a_name_is_located_at_the_step(self):
        (problem,) = validate_yaml("jobs:\n  steps:\n    - wait: 1\n", "String").diagnostics
        assert (problem.code, problem.message) == ("schema-required", "missing required key 'name'")
        assert (problem.path, problem.line, problem.column) == (("jobs", "steps", 0), 3, 7)

    def test_syntax_error_stops_before_the_schema(self):
        assert _codes("jobs:\n  steps: [1, 2\n") == ["yaml-syntax"]


class TestStepValues:
    def test_name_must_be_text(self):
        assert _codes("jobs:\n  steps:\n    - name: 123\n      wait: 1\n") == ["schema-type"]

    def test_wait_given_as_text(self):
        (problem,) = validate_yaml(_step("      wait: '5'\n"), "String").diagnostics
        assert (problem.code, problem.message) == ("schema-type", "expected an integer, got a string")
        assert (problem.path, problem.line, problem.column) == (("jobs", "steps", 0, "wait"), 4, 13)

    def test_wait_given_as_boolean(self):
        (problem,) = validate_yaml(_step("      wait: true\n"), "String").diagnostics
        assert problem.message == "expected an integer, got true or false"

    def test_wait_given_as_fraction(self):
        assert _codes(_step("      wait: 0.5\n")) == ["schema-type"]

    def test_negative_wait(self):
        (problem,) = validate_yaml(_step("      wait: -1\n"), "String").diagnostics
        assert (problem.code, problem.message) == ("schema-minimum", "must be 0 or more, got -1")

    def test_empty_run_path(self):
        assert _codes(_step("      run: ''\n      with: api-runner\n")) == ["schema-min-length"]

    def test_unknown_runner_suggests_the_closest_name(self):
        (problem,) = validate_yaml(_step("      run: a.json\n      with: web-runer\n"), "String").diagnostics
        assert problem.code == "schema-enum"
        assert problem.message == (
            "'web-runer' is not one of: gui-runner, web-runner, api-runner, load-runner, file-runner."
            " Did you mean 'web-runner'?")
        assert (problem.path, problem.line, problem.column) == (("jobs", "steps", 0, "with"), 5, 13)

    def test_runner_without_a_value(self):
        (problem,) = validate_yaml(_step("      run: a.json\n      with:\n"), "String").diagnostics
        assert problem.message == "expected a string, got null"

    def test_unknown_url_open_method(self):
        assert _codes(_step("      open_url: https://example.com\n      url_open_method: tab\n")) == ["schema-enum"]

    def test_unzip_marker_accepts_any_value(self):
        for marker in ("true", "archive.zip", "", "[1, 2]"):
            assert _codes(_step(f"      unzip_zipfile: {marker}\n      zip_file_path: a.zip\n")) == []

    def test_a_type_error_never_echoes_the_value(self):
        text = _step("      unzip_zipfile: true\n      zip_file_path: a.zip\n      password: 13572468\n")
        (problem,) = validate_yaml(text, "String").diagnostics
        assert problem.message == "expected a string, got an integer"

    def test_long_enum_value_is_shortened(self):
        text = _step("      run: a.json\n      with: " + "x" * 200 + "\n")
        (problem,) = validate_yaml(text, "String").diagnostics
        assert len(problem.message) < 200


class TestParallelRun:
    def test_block_must_be_a_mapping(self):
        assert _codes(_step("      parallel_run: [a, b]\n")) == ["schema-type"]

    def test_runners_and_scripts_are_required(self):
        result = validate_yaml(_step("      parallel_run:\n        executor_path: python\n"), "String")
        assert [item.message for item in result.diagnostics] == [
            "missing required key 'runners'", "missing required key 'scripts'"]

    def test_unknown_runner_inside_the_list(self):
        text = _step(
            "      parallel_run:\n        runners: [api-runner, cli-runner]\n        scripts: [a.json, b.json]\n")
        (problem,) = validate_yaml(text, "String").diagnostics
        assert problem.code == "schema-enum"
        assert problem.path == ("jobs", "steps", 0, "parallel_run", "runners", 1)
        assert (problem.line, problem.column) == (5, 31)

    def test_scripts_must_be_text(self):
        text = _step("      parallel_run:\n        runners: [api-runner]\n        scripts: [1]\n")
        assert _codes(text) == ["schema-type"]

    def test_empty_lists(self):
        text = _step("      parallel_run:\n        runners: []\n        scripts: []\n")
        assert _codes(text) == ["schema-min-items", "schema-min-items"]


class TestRunSettings:
    def test_unknown_keep_policy(self):
        (problem,) = validate_yaml("keep_artifacts: sometimes\n" + _step("      wait: 1\n"), "String").diagnostics
        assert (problem.code, problem.path) == ("schema-enum", ("keep_artifacts",))
        assert problem.message == "'sometimes' is not one of: on_failure, always, never."

    def test_unknown_report_format(self):
        (problem,) = validate_yaml("report_formats: [json, pdf]\n" + _step("      wait: 1\n"), "String").diagnostics
        assert (problem.code, problem.path, problem.line, problem.column) == (
            "schema-enum", ("report_formats", 1), 1, 24)

    def test_report_formats_must_be_a_list(self):
        assert _codes("report_formats: html\n" + _step("      wait: 1\n")) == ["schema-type"]

    def test_no_report_format_is_allowed(self):
        assert _codes("report_formats: []\n" + _step("      wait: 1\n")) == []

    def test_empty_paths(self):
        text = "artifacts_path: ''\nreport_path: ''\n" + _step("      wait: 1\n")
        assert _codes(text) == ["schema-min-length", "schema-min-length"]


class TestArtifactPatterns:
    def test_step_artifacts_must_be_a_list(self):
        text = _step("      run: a.json\n      with: api-runner\n      artifacts: reports/*.json\n")
        (problem,) = validate_yaml(text, "String").diagnostics
        assert (problem.code, problem.message) == ("schema-type", "expected a list, got a string")

    def test_step_artifact_patterns_must_be_text(self):
        text = _step("      run: a.json\n      with: api-runner\n      artifacts: [reports, 5, '']\n")
        assert _codes(text) == ["schema-type", "schema-min-length"]

    def test_parallel_artifacts_are_one_list_per_script(self):
        text = _step(
            "      parallel_run:\n        runners: [api-runner]\n        scripts: [a.json]\n"
            "        artifacts: ['reports/*.json']\n")
        (problem,) = validate_yaml(text, "String").diagnostics
        assert (problem.code, problem.path) == (
            "schema-type", ("jobs", "steps", 0, "parallel_run", "artifacts", 0))
        assert problem.message == "expected a list, got a string"


class TestOrdering:
    def test_diagnostics_come_in_document_order(self):
        text = (
            "jobs:\n  steps:\n"
            "    - name: a\n      wait: x\n"
            "    - name: b\n      run: a.json\n      with: nope\n"
        )
        lines = [item.line for item in validate_yaml(text, "String").diagnostics]
        assert lines == [4, 7]


def _corpus() -> list:
    """Workflows that put every kind of value under every key the schema knows, and under one it does not."""
    values = ["x", "", 5, -1, 0, 1.5, True, None, [], ["a"], [1], {}, {"a": 1}, "web-runner", "nope",
              ["web-runner", "bad"], ["a.json", ""]]
    schema = get_yaml_schema()
    step = {"name": "a", "wait": 1}
    documents = [None, [], "text", {}, {"jobs": {"steps": [None]}}, {"jobs": {"steps": [{}]}}]
    for key, value in itertools.product([*schema["properties"], "other"], values):
        documents.append({"jobs": {"steps": [step]}, key: value})
    for key, value in itertools.product([*schema["$defs"]["step"]["properties"], "other"], values):
        documents.append({"jobs": {"steps": [{"name": "a", key: value}, {key: value}]}})
    for key, value in itertools.product([*schema["$defs"]["parallel_run"]["properties"], "other"], values):
        complete = {"runners": ["api-runner"], "scripts": ["a.json"], key: value}
        documents.append({"jobs": {"steps": [{"name": "a", "parallel_run": complete},
                                            {"name": "b", "parallel_run": {key: value}}]}})
    return documents


def test_built_in_validator_agrees_with_the_reference_implementation():
    """With ``jsonschema`` installed, both validators reject the same paths of every corpus document."""
    jsonschema = pytest.importorskip("jsonschema")  # reason: not a dependency of test_pioneer
    reference = jsonschema.Draft202012Validator(get_yaml_schema())
    disagreements = []
    for document in _corpus():
        expected = {tuple(error.absolute_path) for error in reference.iter_errors(document)}
        found = {item.path for item in validate_yaml(yaml.safe_dump(document), "String").diagnostics}
        if expected != found:
            disagreements.append(document)
    assert disagreements == []


class TestHelpers:
    @pytest.mark.parametrize("value, expected", [
        (None, "null"), (True, "boolean"), (3, "integer"), (1.5, "number"), ("a", "string"),
        ([], "array"), ({}, "object"), ({1}, "set"),
    ])
    def test_json_type(self, value, expected):
        assert json_type(value) == expected

    def test_suggestion_only_for_a_close_word(self):
        assert suggestion("wiat", ["wait", "run"]) == " Did you mean 'wait'?"
        assert suggestion("zzz", ["wait", "run"]) == ""

    def test_number_accepts_an_integer(self):
        document = load_yaml("3", "String")
        assert list(_SchemaChecker({}, document).check(3, {"type": "number"}, ())) == []

    def test_reference_outside_the_schema_is_rejected(self):
        document = load_yaml("a: 1", "String")
        with pytest.raises(ValueError, match="unsupported schema reference"):
            list(_SchemaChecker({}, document).check({}, {"$ref": "https://example.com/other.json"}, ()))
