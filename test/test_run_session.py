"""Tests for the run session: what ``execute_yaml`` records, keeps and returns."""
import json
import logging
import os
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from test_pioneer import RunOptions, execute_yaml
from test_pioneer.artifacts.context import ENV_ARTIFACT_DIR, ENV_RUN_ID
from test_pioneer.artifacts.session import current_session
from test_pioneer.executor.run.executor_run import run
from test_pioneer.models.result import Status
from test_pioneer.utils.exception.exceptions import WrongInputException, YamlException

EXECUTOR = "test_pioneer.executor.pioneer_executor"
PASSING = "jobs:\n  steps:\n    - name: pause\n      wait: 0\n"
FAILING = (
    "jobs:\n  steps:\n"
    "    - name: first\n      wait: 0\n"
    "    - name: broken\n      open_url: https://example.com\n      url_open_method: nope\n"
    "    - name: never\n      wait: 0\n"
)
RUN_STEP = "jobs:\n  steps:\n    - name: api\n      run: case.json\n      with: api-runner\n"


def _manifest(run_id: str, root: str = "artifacts") -> dict:
    return json.loads((Path(root) / run_id / "testpioneer" / "manifest.json").read_text(encoding="utf-8"))


def _fake_runner(output: str = "ran", error: Exception | None = None):
    """Return a stand-in for a runner's ``execute_action`` that records the environment it saw."""
    seen = {}

    def execute(_actions):
        seen[ENV_RUN_ID] = os.environ.get(ENV_RUN_ID)
        seen[ENV_ARTIFACT_DIR] = os.environ.get(ENV_ARTIFACT_DIR)
        print(output)
        if error is not None:
            raise error
    return execute, seen


@pytest.fixture
def script():
    """A JSON action file in the working directory."""
    Path("case.json").write_text("[]", encoding="utf-8")


class TestResult:
    def test_a_passing_run_returns_its_result(self):
        result = execute_yaml(PASSING, "String")
        assert result.status is Status.PASSED
        assert re.fullmatch(r"\d{8}T\d{6}Z-[0-9a-f]{8}", result.run_id)
        assert result.workflow is None
        assert [(step.name, step.action, step.status) for step in result.steps] == [
            ("pause", "wait", Status.PASSED)]
        assert result.started_at <= result.finished_at
        assert result.warnings == []

    def test_a_file_workflow_is_named_in_the_result(self, tmp_path):
        path = tmp_path / "flow.yml"
        path.write_text(PASSING, encoding="utf-8")
        assert execute_yaml(str(path)).workflow == str(path)

    def test_a_failed_step_stops_the_run_and_cancels_the_rest(self):
        result = execute_yaml(FAILING, "String")
        assert result.status is Status.FAILED
        assert [(step.name, step.status) for step in result.steps] == [
            ("first", Status.PASSED), ("broken", Status.FAILED), ("never", Status.CANCELLED)]
        assert result.steps[1].message == "Invalid url_open_method: nope"
        assert result.steps[2].message is None

    def test_duplicate_step_names_fail_the_run_with_the_reason(self):
        text = "jobs:\n  steps:\n    - name: dup\n      wait: 0\n    - name: dup\n      wait: 0\n"
        result = execute_yaml(text, "String")
        assert result.status is Status.ERROR
        assert result.message == "job name duplicated: dup"
        assert result.steps == []

    def test_the_caller_can_name_the_run(self):
        assert execute_yaml(PASSING, "String", RunOptions(run_id="nightly-7")).run_id == "nightly-7"

    def test_an_unsafe_run_id_is_refused(self):
        with pytest.raises(WrongInputException):
            execute_yaml(PASSING, "String", RunOptions(run_id="../elsewhere"))


class TestKeepPolicy:
    def test_a_passing_run_leaves_nothing_by_default(self):
        result = execute_yaml(PASSING, "String")
        assert result.artifact_dir is None
        assert not Path("artifacts").exists()

    def test_a_failed_run_keeps_its_log_and_manifest(self):
        result = execute_yaml(FAILING, "String", RunOptions(run_id="r1"))
        run_dir = Path("artifacts") / "r1"
        assert result.artifact_dir == str(run_dir)
        assert _manifest("r1") == result.to_dict()
        log = (run_dir / "testpioneer" / "execution.log").read_text(encoding="utf-8")
        assert "| INFO | Run r1 started: inline YAML" in log
        assert "| ERROR | Invalid url_open_method: nope" in log
        assert "| INFO | Step 'broken' finished: failed" in log
        assert "| INFO | Run r1 finished: failed" in log

    def test_always_keeps_a_passing_run(self):
        result = execute_yaml("keep_artifacts: always\n" + PASSING, "String", RunOptions(run_id="r1"))
        assert result.status is Status.PASSED
        assert _manifest("r1")["status"] == "passed"

    def test_never_keeps_nothing_of_a_failed_run(self):
        result = execute_yaml("keep_artifacts: never\n" + FAILING, "String")
        assert result.status is Status.FAILED
        assert result.artifact_dir is None
        assert not Path("artifacts").exists()

    def test_the_option_overrides_the_workflow(self):
        options = RunOptions(run_id="r1", keep_artifacts="always", artifacts_path="from_option")
        execute_yaml("keep_artifacts: never\nartifacts_path: from_yaml\n" + PASSING, "String", options)
        assert _manifest("r1", "from_option")["run_id"] == "r1"
        assert not Path("from_yaml").exists()

    def test_the_workflow_can_place_the_artifacts(self):
        execute_yaml("artifacts_path: out/runs\nkeep_artifacts: always\n" + PASSING, "String", RunOptions(run_id="r1"))
        assert _manifest("r1", "out/runs")["run_id"] == "r1"

    def test_two_runs_do_not_share_a_directory(self):
        first = execute_yaml("keep_artifacts: always\n" + PASSING, "String")
        second = execute_yaml("keep_artifacts: always\n" + PASSING.replace("pause", "again"), "String")
        assert first.run_id != second.run_id
        assert sorted(path.name for path in Path("artifacts").iterdir()) == sorted([first.run_id, second.run_id])

    def test_an_unknown_policy_is_refused(self):
        with pytest.raises(YamlException, match="keep_artifacts must be one of on_failure, always, never"):
            execute_yaml("keep_artifacts: sometimes\n" + PASSING, "String")

    def test_a_path_that_is_not_text_is_refused(self):
        with pytest.raises(YamlException, match="artifacts_path must be a non-empty string"):
            execute_yaml("artifacts_path: 5\n" + PASSING, "String")


class TestFailuresDoNotMaskTheRun:
    def test_an_unwritable_artifact_root_only_adds_a_warning(self):
        Path("blocked").write_text("a file where the directory should go", encoding="utf-8")
        result = execute_yaml("artifacts_path: blocked\n" + FAILING, "String")
        assert result.status is Status.FAILED
        assert result.artifact_dir is None
        assert len(result.warnings) == 1
        assert result.warnings[0].startswith("artifacts are not collected:")

    def test_an_exception_is_raised_as_before_and_recorded(self):
        with patch(f"{EXECUTOR}.blocked_wait", side_effect=RuntimeError("boom")), \
                pytest.raises(RuntimeError, match="boom"):
            execute_yaml(PASSING + "    - name: after\n      wait: 0\n", "String", RunOptions(run_id="r1"))
        manifest = _manifest("r1")
        assert manifest["status"] == "error"
        assert manifest["message"] == "RuntimeError('boom')"
        assert [(step["name"], step["status"]) for step in manifest["steps"]] == [
            ("pause", "error"), ("after", "cancelled")]

    def test_a_workflow_without_jobs_raises_and_is_recorded(self):
        with pytest.raises(YamlException, match="No jobs tag"):
            execute_yaml("key: value", "String", RunOptions(run_id="r1"))
        manifest = _manifest("r1")
        assert manifest["status"] == "error"
        assert manifest["steps"] == []


class TestStepLog:
    def test_step_messages_reach_the_run_log_without_pioneer_log(self, caplog):
        with caplog.at_level(logging.DEBUG, logger="TestPioneer"):
            execute_yaml(FAILING, "String", RunOptions(run_id="r1"))
        log = (Path("artifacts") / "r1" / "testpioneer" / "execution.log").read_text(encoding="utf-8")
        assert "| INFO | Wait seconds: 0" in log
        # The public logger stays as quiet as it was: it only speaks when pioneer_log is set.
        assert caplog.records == []

    def test_no_session_is_left_behind(self):
        execute_yaml(PASSING, "String")
        assert current_session() is None
        with pytest.raises(YamlException):
            execute_yaml("key: value", "String")
        assert current_session() is None


@pytest.mark.usefixtures("script")
class TestInProcessRunner:
    def test_a_runner_call_is_recorded_with_its_environment_and_output(self, capsys):
        execute, seen = _fake_runner("hello from the runner")
        with patch("test_pioneer.executor.run.executor_run.select_with_runner", return_value=(True, execute)):
            result = execute_yaml("keep_artifacts: always\n" + RUN_STEP, "String", RunOptions(run_id="r1"))
        (runner,) = result.runners
        assert (runner.runner, runner.script, runner.step, runner.status) == (
            "api-runner", "case.json", "api", Status.PASSED)
        assert runner.exit_code is None
        assert runner.artifact_dir == "runners/api-runner/01-api"
        directory = Path("artifacts") / "r1" / runner.artifact_dir
        assert seen == {ENV_RUN_ID: "r1", ENV_ARTIFACT_DIR: str(directory.resolve())}
        assert (directory / "stdout.log").read_text(encoding="utf-8") == "hello from the runner\n"
        assert [item.path for item in runner.artifacts] == ["runners/api-runner/01-api/stdout.log"]
        assert capsys.readouterr().out == "hello from the runner\n"

    def test_the_environment_is_put_back(self, monkeypatch):
        monkeypatch.setenv(ENV_RUN_ID, "outer")
        monkeypatch.delenv(ENV_ARTIFACT_DIR, raising=False)
        execute, seen = _fake_runner()
        with patch("test_pioneer.executor.run.executor_run.select_with_runner", return_value=(True, execute)):
            execute_yaml(RUN_STEP, "String", RunOptions(run_id="inner"))
        assert seen[ENV_RUN_ID] == "inner"
        assert os.environ[ENV_RUN_ID] == "outer"
        assert ENV_ARTIFACT_DIR not in os.environ

    def test_a_passing_runner_leaves_nothing_by_default(self):
        execute, _seen = _fake_runner()
        with patch("test_pioneer.executor.run.executor_run.select_with_runner", return_value=(True, execute)):
            result = execute_yaml(RUN_STEP, "String")
        assert result.runners[0].artifact_dir is None
        assert not Path("artifacts").exists()

    def test_a_runner_that_raises_keeps_what_it_printed(self):
        execute, _seen = _fake_runner("last words", error=ValueError("bad action list"))
        with patch("test_pioneer.executor.run.executor_run.select_with_runner", return_value=(True, execute)), \
                pytest.raises(ValueError, match="bad action list"):
            execute_yaml(RUN_STEP, "String", RunOptions(run_id="r1"))
        manifest = _manifest("r1")
        (runner,) = manifest["runners"]
        assert (runner["status"], runner["message"]) == ("error", "ValueError('bad action list')")
        assert manifest["steps"][0]["status"] == "error"
        kept = Path("artifacts") / "r1" / runner["artifact_dir"] / "stdout.log"
        assert kept.read_text(encoding="utf-8") == "last words\n"

    def test_a_step_refused_before_its_runner_starts_still_has_a_runner_entry(self):
        execute, _seen = _fake_runner()
        text = RUN_STEP.replace("case.json", "absent.json")
        with patch("test_pioneer.executor.run.executor_run.select_with_runner", return_value=(True, execute)):
            result = execute_yaml(text, "String")
        (runner,) = result.runners
        assert (runner.runner, runner.script, runner.status) == ("api-runner", "absent.json", Status.ERROR)
        assert runner.message == "File does not exist: absent.json"
        assert result.steps[0].status is Status.ERROR
        assert result.status is Status.ERROR

    def test_a_handler_called_on_its_own_records_nothing(self, capsys):
        execute, seen = _fake_runner("direct call")
        with patch("test_pioneer.executor.run.executor_run.select_with_runner", return_value=(True, execute)):
            assert run({"run": "case.json", "with": "api-runner"}) is True
        assert seen == {ENV_RUN_ID: None, ENV_ARTIFACT_DIR: None}
        assert not Path("artifacts").exists()
        assert capsys.readouterr().out == "direct call\n"
