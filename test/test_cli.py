"""Tests for test_pioneer.cli: the ``python -m test_pioneer`` command line."""
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from test_pioneer import get_yaml_schema
from test_pioneer.cli import main
from test_pioneer.schema import SCHEMA_VERSION
from test_pioneer.utils.exception.exceptions import ExecutorException

REPO_ROOT = Path(__file__).resolve().parents[1]
VALID = "jobs:\n  steps:\n    - name: pause\n      wait: 1\n"
INVALID = "jobs:\n  steps:\n    - name: pause\n      wait: soon\n"
WARNING_ONLY = "jobs:\n  steps:\n    - name: pause\n      wait: 1\n      note: later\n"
RUNNABLE = "jobs:\n  steps:\n    - name: pause\n      wait: 0\n"
NOT_RUNNABLE = "jobs:\n  steps:\n    - name: page\n      open_url: https://example.com\n      url_open_method: nope\n"
NEEDS_SCRIPT = "jobs:\n  steps:\n    - name: api\n      run: cases/a.json\n      with: api-runner\n"


@pytest.fixture(autouse=True)
def every_runner_installed(monkeypatch):
    """Keep the result independent of which runner packages this machine has."""
    monkeypatch.setattr("test_pioneer.validation.linter.is_installed", lambda package: True)


def _write(tmp_path, name: str, text: str) -> str:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return str(path)


class TestValidateCommand:
    def test_valid_file_exits_zero(self, tmp_path, capsys):
        assert main(["validate", _write(tmp_path, "ok.yml", VALID)]) == 0
        assert capsys.readouterr().out == "Checked 1 file(s): 0 error(s), 0 warning(s)\n"

    def test_invalid_file_exits_one_and_locates_the_problem(self, tmp_path, capsys):
        path = _write(tmp_path, "bad.yml", INVALID)
        assert main(["validate", path]) == 1
        lines = capsys.readouterr().out.splitlines()
        assert lines == [
            f"{path}:4:13: error: jobs.steps[0].wait: expected an integer, got a string [schema-type]",
            "Checked 1 file(s): 1 error(s), 0 warning(s)",
        ]

    def test_warning_does_not_fail_by_default(self, tmp_path, capsys):
        assert main(["validate", _write(tmp_path, "warn.yml", WARNING_ONLY)]) == 0
        assert "warning: jobs.steps[0].note: unknown key 'note' is ignored. [unknown-key]" in capsys.readouterr().out

    def test_strict_turns_a_warning_into_a_failure(self, tmp_path):
        assert main(["validate", "--strict", _write(tmp_path, "warn.yml", WARNING_ONLY)]) == 1

    def test_one_bad_file_among_several_fails_the_command(self, tmp_path, capsys):
        good = _write(tmp_path, "ok.yml", VALID)
        bad = _write(tmp_path, "bad.yml", INVALID)
        assert main(["validate", good, bad]) == 1
        assert capsys.readouterr().out.splitlines()[-1] == "Checked 2 file(s): 1 error(s), 0 warning(s)"

    def test_missing_file_is_reported_without_a_position(self, tmp_path, capsys):
        path = str(tmp_path / "absent.yml")
        assert main(["validate", path]) == 1
        assert capsys.readouterr().out.startswith(f"{path}: error: <root>: cannot read the workflow file")

    def test_base_dir_is_where_scripts_are_looked_up(self, tmp_path, capsys):
        (tmp_path / "project" / "cases").mkdir(parents=True)
        (tmp_path / "project" / "cases" / "a.json").write_text("[]", encoding="utf-8")
        path = _write(tmp_path, "flow.yml", NEEDS_SCRIPT)
        assert main(["validate", "--strict", "--base_dir", str(tmp_path / "project"), path]) == 0
        assert main(["validate", "--strict", "--base_dir", str(tmp_path), path]) == 1
        assert "[missing-file]" in capsys.readouterr().out

    def test_file_check_can_be_skipped(self, tmp_path):
        path = _write(tmp_path, "flow.yml", NEEDS_SCRIPT)
        assert main(["validate", "--strict", "--no_file_check", "--base_dir", str(tmp_path), path]) == 0

    def test_validate_needs_a_file(self):
        with pytest.raises(SystemExit) as stopped:
            main(["validate"])
        assert stopped.value.code == 2


class TestJsonFormat:
    def test_report_carries_structured_diagnostics(self, tmp_path, capsys):
        path = _write(tmp_path, "bad.yml", INVALID)
        assert main(["validate", "--format", "json", path]) == 1
        report = json.loads(capsys.readouterr().out)
        assert report["schema_version"] == SCHEMA_VERSION
        assert report["ok"] is False
        (entry,) = report["files"]
        assert entry["source"] == path
        assert entry["errors"] == 1
        assert entry["diagnostics"] == [{
            "severity": "error", "code": "schema-type", "message": "expected an integer, got a string",
            "path": ["jobs", "steps", 0, "wait"], "pointer": "jobs.steps[0].wait",
            "line": 4, "column": 13, "source": "schema",
        }]

    def test_strict_marks_a_warning_only_report_as_failed(self, tmp_path, capsys):
        path = _write(tmp_path, "warn.yml", WARNING_ONLY)
        assert main(["validate", "--format", "json", "--strict", path]) == 1
        report = json.loads(capsys.readouterr().out)
        assert report["ok"] is False
        assert report["files"][0]["ok"] is True

    def test_non_ascii_names_stay_ascii_safe(self, tmp_path, capsys):
        text = "jobs:\n  steps:\n    - name: 步驟\n      wait: 1\n    - name: 步驟\n      wait: 1\n"
        assert main(["validate", "--format", "json", _write(tmp_path, "dup.yml", text)]) == 1
        output = capsys.readouterr().out
        assert output.isascii()
        assert "步驟" in json.loads(output)["files"][0]["diagnostics"][0]["message"]


class TestSchemaCommand:
    def test_schema_is_printed(self, capsys):
        assert main(["schema"]) == 0
        assert json.loads(capsys.readouterr().out) == get_yaml_schema()

    def test_schema_is_written_to_a_file(self, tmp_path, capsys):
        target = tmp_path / "workflow.schema.json"
        assert main(["schema", "-o", str(target)]) == 0
        assert capsys.readouterr().out == ""
        assert json.loads(target.read_text(encoding="utf-8")) == get_yaml_schema()


class TestRunCommand:
    def test_a_passing_run_exits_zero_and_is_summarised(self, tmp_path, capsys):
        assert main(["run", "--run_id", "r1", _write(tmp_path, "ok.yml", RUNNABLE)]) == 0
        assert capsys.readouterr().out.splitlines() == [
            "Run r1 passed: 0 runner execution(s)",
            f"Report: {Path('report') / 'testpioneer-report.json'}",
            f"Report: {Path('report') / 'testpioneer-report.html'}",
        ]

    def test_a_failed_run_exits_one_and_names_its_artifacts(self, tmp_path, capsys):
        assert main(["run", "--run_id", "r1", _write(tmp_path, "bad.yml", NOT_RUNNABLE)]) == 1
        expected = Path("artifacts") / "r1"
        assert capsys.readouterr().out.splitlines()[0] == (
            f"Run r1 failed: 0 runner execution(s); artifacts: {expected}")
        assert (expected / "testpioneer" / "manifest.json").is_file()

    def test_report_options_are_passed_on(self, tmp_path, capsys):
        path = _write(tmp_path, "ok.yml", RUNNABLE)
        assert main(["run", "--report_path", "out", "--report_formats", "junit", path]) == 0
        assert [item.name for item in Path("out").iterdir()] == ["testpioneer-junit.xml"]
        assert capsys.readouterr().out.splitlines()[1:] == [f"Report: {Path('out') / 'testpioneer-junit.xml'}"]

    def test_no_report_format_writes_no_report(self, tmp_path, capsys):
        assert main(["run", "--run_id", "r1", "--report_formats", "none", _write(tmp_path, "ok.yml", RUNNABLE)]) == 0
        assert capsys.readouterr().out == "Run r1 passed: 0 runner execution(s)\n"
        assert not Path("report").exists()

    def test_several_report_formats_are_separated_by_commas(self, tmp_path):
        path = _write(tmp_path, "ok.yml", RUNNABLE)
        assert main(["run", "--report_formats", "json, junit", path]) == 0
        assert sorted(item.name for item in Path("report").iterdir()) == [
            "testpioneer-junit.xml", "testpioneer-report.json"]

    @pytest.mark.parametrize("value", ["pdf", "json,pdf", "", ","])
    def test_an_unknown_report_format_is_a_usage_error(self, tmp_path, value):
        with pytest.raises(SystemExit) as stopped:
            main(["run", "--report_formats", value, _write(tmp_path, "ok.yml", RUNNABLE)])
        assert stopped.value.code == 2

    def test_artifact_options_are_passed_on(self, tmp_path):
        path = _write(tmp_path, "ok.yml", RUNNABLE)
        assert main(["run", "--run_id", "r1", "--artifacts_path", "kept", "--keep_artifacts", "always", path]) == 0
        assert (Path("kept") / "r1" / "testpioneer" / "execution.log").is_file()

    def test_an_unknown_keep_policy_is_a_usage_error(self, tmp_path):
        with pytest.raises(SystemExit) as stopped:
            main(["run", "--keep_artifacts", "sometimes", _write(tmp_path, "ok.yml", RUNNABLE)])
        assert stopped.value.code == 2

    def test_a_warning_goes_to_standard_error(self, tmp_path, capsys):
        Path("blocked").write_text("a file where the directory should go", encoding="utf-8")
        assert main(["run", "--artifacts_path", "blocked", _write(tmp_path, "ok.yml", RUNNABLE)]) == 0
        assert capsys.readouterr().err.startswith("warning: artifacts are not collected:")


class TestExecuteFlag:
    def test_execute_flag_still_exits_zero_for_a_failed_run(self, tmp_path):
        assert main(["-e", _write(tmp_path, "bad.yml", NOT_RUNNABLE)]) == 0

    @patch("test_pioneer.cli.execute_yaml")
    def test_short_flag_executes_the_file(self, mock_execute):
        assert main(["-e", "flow.yml"]) == 0
        mock_execute.assert_called_once_with("flow.yml")

    @patch("test_pioneer.cli.execute_yaml")
    def test_long_flag_executes_the_file(self, mock_execute):
        assert main(["--execute_yaml", "flow.yml"]) == 0
        mock_execute.assert_called_once_with("flow.yml")

    def test_no_argument_raises(self):
        with pytest.raises(ExecutorException, match="execute_yaml have no argument"):
            main([])


def test_module_entry_point_returns_the_exit_code(tmp_path):
    """``python -m test_pioneer validate`` exits 1 for an invalid workflow and 0 for a valid one."""
    bad = _write(tmp_path, "bad.yml", INVALID)
    good = _write(tmp_path, "ok.yml", VALID)
    command = [sys.executable, "-m", "test_pioneer", "validate"]
    # The child starts in the test's scratch directory, so the checkout is put on its import path.
    environment = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
    failed = subprocess.run(command + [bad], capture_output=True, text=True, timeout=120, check=False,
                            env=environment)
    passed = subprocess.run(command + [good], capture_output=True, text=True, timeout=120, check=False,
                            env=environment)
    assert failed.returncode == 1
    assert "[schema-type]" in failed.stdout
    assert passed.returncode == 0
