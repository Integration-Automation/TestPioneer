"""``parallel_run`` inside a run: real sub-processes, their artifacts and their results.

The runner is a small stand-in package with the family's ``--execute_file`` command line, so the
tests start real processes without needing a browser or a server.
"""
import json
from pathlib import Path

import pytest

from test_pioneer import RunOptions, execute_yaml
from test_pioneer.executor.run import parallel_run as parallel_run_module
from test_pioneer.executor.run.parallel_run import parallel_run
from test_pioneer.models.result import Status
from test_pioneer.runner import registry
from test_pioneer.runner.adapter import ModuleRunner

FAKE_RUNNER = '''
import argparse, json, os, sys, time
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--execute_file")
plan = json.loads(Path(parser.parse_args().execute_file).read_text(encoding="utf-8"))
print("out:", plan["say"], flush=True)
print("err:", plan["say"], file=sys.stderr, flush=True)
directory = os.environ.get("TEST_PIONEER_ARTIFACT_DIR")
if directory:
    Path(directory, "report.json").write_text(
        json.dumps({"run_id": os.environ.get("TEST_PIONEER_RUN_ID")}), encoding="utf-8")
time.sleep(plan.get("sleep", 0))
sys.exit(plan.get("exit", 0))
'''


@pytest.fixture(autouse=True)
def fake_runner(tmp_path_factory, monkeypatch):
    """Register ``fake-runner`` and put its package on the import path of the sub-processes."""
    package = tmp_path_factory.mktemp("packages") / "fake_runner"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "__main__.py").write_text(FAKE_RUNNER, encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(package.parent))
    monkeypatch.setattr(registry, "RUNNERS", {
        **registry.RUNNERS, "fake-runner": ModuleRunner("fake-runner", "fake_runner")})
    monkeypatch.setitem(parallel_run_module._BASE_RUNNER_COMMANDS, "fake-runner", "fake_runner")


def _script(name: str, **plan) -> str:
    Path(name).write_text(json.dumps({"say": Path(name).stem, **plan}), encoding="utf-8")
    return name


def _workflow(*scripts: str, runners: list | None = None, extra: str = "") -> str:
    names = runners or ["fake-runner"] * len(scripts)
    return (
        f"{extra}jobs:\n  steps:\n    - name: together\n      parallel_run:\n"
        f"        runners: {json.dumps(names)}\n        scripts: {json.dumps(list(scripts))}\n"
        "    - name: afterwards\n      wait: 0\n"
    )


def _manifest(run_id: str) -> dict:
    return json.loads((Path("artifacts") / run_id / "testpioneer" / "manifest.json").read_text(encoding="utf-8"))


class TestOneFailsOneSucceeds:
    @pytest.fixture
    def result(self):
        return execute_yaml(_workflow(_script("good.json"), _script("bad.json", exit=3)),
                            "String", RunOptions(run_id="r1"))

    def test_each_runner_has_its_exit_code_and_status(self, result):
        good, bad = result.runners
        assert (good.runner, good.step, good.status, good.exit_code, good.message) == (
            "fake-runner", "together", Status.PASSED, 0, None)
        assert (bad.status, bad.exit_code, bad.message) == (Status.FAILED, 3, "exit code 3")
        assert (good.script, bad.script) == ("good.json", "bad.json")
        assert bad.duration_ms >= 0 and bad.started_at <= bad.finished_at

    def test_the_step_and_the_run_fail_but_later_steps_still_run(self, result):
        assert [(step.name, step.status) for step in result.steps] == [
            ("together", Status.FAILED), ("afterwards", Status.PASSED)]
        assert result.status is Status.FAILED
        assert result.summary() == {"passed": 1, "failed": 1, "error": 0, "cancelled": 0, "total": 2}

    def test_the_failed_runner_keeps_its_output_and_what_it_wrote(self, result):
        bad = result.runners[1]
        assert bad.artifact_dir == "runners/fake-runner/02-together-2"
        directory = Path("artifacts") / "r1" / bad.artifact_dir
        assert (directory / "stdout.log").read_text(encoding="utf-8").split() == ["out:", "bad"]
        assert (directory / "stderr.log").read_text(encoding="utf-8").split() == ["err:", "bad"]
        assert json.loads((directory / "report.json").read_text(encoding="utf-8")) == {"run_id": "r1"}
        assert [(item.path, item.kind) for item in bad.artifacts] == [
            ("runners/fake-runner/02-together-2/report.json", "report"),
            ("runners/fake-runner/02-together-2/stderr.log", "log"),
            ("runners/fake-runner/02-together-2/stdout.log", "log"),
        ]

    def test_the_runner_that_passed_keeps_nothing(self, result):
        assert result.runners[0].artifact_dir is None
        assert result.runners[0].artifacts == []
        assert [path.name for path in (Path("artifacts") / "r1" / "runners" / "fake-runner").iterdir()] == [
            "02-together-2"]

    def test_the_manifest_records_the_run(self, result):
        manifest = _manifest("r1")
        assert manifest == result.to_dict()
        assert [(runner["exit_code"], runner["status"]) for runner in manifest["runners"]] == [
            (0, "passed"), (3, "failed")]


class TestKeepPolicy:
    def test_always_keeps_the_runner_that_passed_too(self):
        result = execute_yaml(_workflow(_script("good.json"), _script("bad.json", exit=1),
                                        extra="keep_artifacts: always\n"), "String", RunOptions(run_id="r1"))
        assert [runner.artifact_dir for runner in result.runners] == [
            "runners/fake-runner/01-together-1", "runners/fake-runner/02-together-2"]
        assert (Path("artifacts") / "r1" / "runners" / "fake-runner" / "01-together-1" / "stdout.log").is_file()

    def test_a_run_whose_runners_all_passed_leaves_nothing(self):
        result = execute_yaml(_workflow(_script("one.json"), _script("two.json")), "String")
        assert result.status is Status.PASSED
        assert [runner.exit_code for runner in result.runners] == [0, 0]
        assert not Path("artifacts").exists()


class TestConsole:
    def test_runner_output_is_still_shown(self, capfd):
        execute_yaml(_workflow(_script("good.json"), _script("bad.json", exit=1)), "String")
        shown = capfd.readouterr()
        assert sorted(shown.out.splitlines()) == ["out: bad", "out: good"]
        assert sorted(shown.err.splitlines()) == ["err: bad", "err: good"]


class TestRunnersThatCannotStart:
    def test_missing_script_and_unknown_runner_are_errors_and_the_rest_runs(self):
        text = _workflow(_script("good.json"), "absent.json", _script("other.json"),
                         runners=["fake-runner", "fake-runner", "cli-runner"])
        result = execute_yaml(text, "String", RunOptions(run_id="r1"))
        good, absent, unknown = result.runners
        assert good.status is Status.PASSED
        assert (absent.status, absent.message) == (Status.ERROR, "Script file does not exist: absent.json")
        assert (unknown.runner, unknown.status, unknown.message) == (
            "cli-runner", Status.ERROR, "Unknown runner type: cli-runner")
        assert result.steps[0].status is Status.ERROR
        assert result.status is Status.ERROR
        assert _manifest("r1")["summary"]["error"] == 2

    def test_a_python_that_does_not_exist_is_an_error(self):
        text = _workflow(_script("good.json")).replace(
            "      parallel_run:\n", "      parallel_run:\n        executor_path: no-such-python-here\n")
        result = execute_yaml(text, "String")
        (runner,) = result.runners
        assert runner.status is Status.ERROR
        assert runner.message.startswith("could not start:")
        assert runner.exit_code is None


class TestOutsideARun:
    def test_the_handler_called_on_its_own_starts_the_process_and_records_nothing(self, capfd):
        step = {"parallel_run": {"runners": ["fake-runner"], "scripts": [_script("solo.json", exit=2)]}}
        assert parallel_run(step) is True
        assert capfd.readouterr().out.split() == ["out:", "solo"]
        assert not Path("artifacts").exists()


class TestInterruption:
    def test_an_interrupted_wait_stops_the_runners_and_records_them_as_cancelled(self, monkeypatch):
        def interrupt(_seconds):
            raise KeyboardInterrupt

        script = _script("slow.json", sleep=60)
        monkeypatch.setattr(parallel_run_module.time, "sleep", interrupt)
        with pytest.raises(KeyboardInterrupt):
            execute_yaml(_workflow(script), "String", RunOptions(run_id="r1"))
        manifest = _manifest("r1")
        (runner,) = manifest["runners"]
        assert (runner["status"], runner["message"]) == ("cancelled", "interrupted")
        assert [(step["name"], step["status"]) for step in manifest["steps"]] == [
            ("together", "cancelled"), ("afterwards", "cancelled")]
        assert (manifest["status"], manifest["message"]) == ("cancelled", "interrupted")
