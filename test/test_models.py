"""Tests for test_pioneer.models"""
import re

from test_pioneer.models.diagnostic import Diagnostic, Severity, ValidationResult, format_path
from test_pioneer.models.result import (
    RESULT_FORMAT_VERSION,
    Artifact,
    RunnerResult,
    RunResult,
    Status,
    StepResult,
    utc_now,
    worst_status,
)


class TestFormatPath:
    def test_root(self):
        assert format_path(()) == "<root>"

    def test_keys_and_indexes(self):
        assert format_path(("jobs", "steps", 0, "with")) == "jobs.steps[0].with"

    def test_nested_indexes(self):
        assert format_path(("jobs", "steps", 2, "parallel_run", "runners", 1)) == \
            "jobs.steps[2].parallel_run.runners[1]"


class TestDiagnostic:
    def test_to_dict_has_path_pointer_and_position(self):
        item = Diagnostic(Severity.ERROR, "schema-type", "expected a string", ("jobs", "steps", 0), 4, 7, "schema")
        assert item.to_dict() == {
            "severity": "error", "code": "schema-type", "message": "expected a string",
            "path": ["jobs", "steps", 0], "pointer": "jobs.steps[0]", "line": 4, "column": 7,
            "source": "schema",
        }

    def test_result_separates_errors_from_warnings(self):
        error = Diagnostic(Severity.ERROR, "a", "broken")
        warning = Diagnostic(Severity.WARNING, "b", "odd")
        result = ValidationResult((error, warning), "flow.yml")
        assert result.errors == (error,)
        assert result.warnings == (warning,)
        assert result.ok is False

    def test_warnings_alone_keep_a_result_ok(self):
        result = ValidationResult((Diagnostic(Severity.WARNING, "b", "odd"),))
        assert result.ok is True
        assert result.to_dict()["warnings"] == 1

    def test_result_to_dict_counts(self):
        result = ValidationResult((Diagnostic(Severity.ERROR, "a", "broken"),), "flow.yml")
        payload = result.to_dict()
        assert payload["source"] == "flow.yml"
        assert payload["ok"] is False
        assert payload["errors"] == 1
        assert payload["diagnostics"][0]["code"] == "a"


class TestStatus:
    def test_error_outranks_everything(self):
        assert worst_status([Status.PASSED, Status.FAILED, Status.ERROR, Status.CANCELLED]) is Status.ERROR

    def test_failed_outranks_cancelled(self):
        assert worst_status([Status.CANCELLED, Status.FAILED, Status.PASSED]) is Status.FAILED

    def test_cancelled_outranks_passed(self):
        assert worst_status([Status.PASSED, Status.CANCELLED]) is Status.CANCELLED

    def test_nothing_ran_counts_as_passed(self):
        assert worst_status([]) is Status.PASSED


class TestRunResult:
    def test_utc_now_is_iso_8601_in_utc(self):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", utc_now())

    def test_to_dict_follows_the_normalized_format(self):
        runner = RunnerResult(
            runner="web-runner", script="web.json", step="web", status=Status.FAILED, exit_code=1,
            duration_ms=1234, report="runners/web-runner/report.json",
            artifacts=[Artifact("runners/web-runner/stdout.log", "log", 12)],
        )
        run = RunResult(run_id="r1", status=Status.FAILED, workflow="flow.yml", runners=[runner],
                        steps=[StepResult("web", "run", Status.FAILED, message="exit code 1")])
        payload = run.to_dict()
        assert payload["format_version"] == RESULT_FORMAT_VERSION
        assert payload["run_id"] == "r1"
        assert payload["status"] == "failed"
        assert payload["runners"][0]["exit_code"] == 1
        assert payload["runners"][0]["status"] == "failed"
        assert payload["runners"][0]["artifacts"] == [
            {"path": "runners/web-runner/stdout.log", "kind": "log", "size": 12}]
        assert payload["steps"][0] == {
            "name": "web", "action": "run", "status": "failed", "started_at": "", "finished_at": "",
            "duration_ms": 0, "message": "exit code 1",
        }

    def test_summary_counts_runners_by_status(self):
        run = RunResult(run_id="r1", runners=[
            RunnerResult("api-runner", "a.json", "a", Status.PASSED),
            RunnerResult("api-runner", "b.json", "b", Status.PASSED),
            RunnerResult("web-runner", "c.json", "c", Status.ERROR),
        ])
        assert run.summary() == {"passed": 2, "failed": 0, "error": 1, "cancelled": 0, "total": 3}
