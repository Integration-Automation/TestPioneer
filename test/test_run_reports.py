"""A run from end to end: declared artifacts are collected, runner reports are read and merged."""
import json
import os
import time
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

import pytest

from test_pioneer import RunOptions, execute_yaml
from test_pioneer.executor.run import parallel_run as parallel_run_module
from test_pioneer.models.result import Status
from test_pioneer.report.readers import RecordPairReader
from test_pioneer.runner import registry
from test_pioneer.runner.adapter import ModuleRunner
from test_pioneer.utils.exception.exceptions import YamlException

SELECT = "test_pioneer.executor.run.executor_run.select_with_runner"
PASSING = "jobs:\n  steps:\n    - name: pause\n      wait: 0\n"
RUN_STEP = (
    "jobs:\n  steps:\n    - name: api\n      run: case.json\n      with: api-runner\n"
    "      artifacts: ['reports/api_*.json']\n"
)
PASSED_RECORD = {"request_method": "GET", "request_url": "http://localhost/users"}
FAILED_RECORD = {"http_method": "post", "test_url": "http://localhost/login", "error": "status 500"}

# A stand-in runner: it writes the family's report pair into its artifact directory and exits 0,
# as the real runners do even when a test failed.
FAKE_RUNNER = '''
import argparse, json, os, sys
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--execute_file")
plan = json.loads(Path(parser.parse_args().execute_file).read_text(encoding="utf-8"))
target = Path(plan.get("write_to") or os.environ["TEST_PIONEER_ARTIFACT_DIR"])
target.mkdir(parents=True, exist_ok=True)
passed = {f"Success_Test{i}": {"name": name} for i, name in enumerate(plan.get("passed", []), 1)}
failed = {f"Failure_Test{i}": {"name": name, "error": "boom"} for i, name in enumerate(plan.get("failed", []), 1)}
(target / (plan["report"] + "_success.json")).write_text(json.dumps(passed), encoding="utf-8")
(target / (plan["report"] + "_failure.json")).write_text(plan.get("raw_failure") or json.dumps(failed),
                                                         encoding="utf-8")
sys.exit(0)
'''


@pytest.fixture
def script():
    """A JSON action file and an empty reports folder in the working directory."""
    Path("case.json").write_text("[]", encoding="utf-8")
    Path("reports").mkdir()


def _reporting_runner(success: dict | None = None, failure: dict | None = None, name: str = "reports/api_run"):
    """Return a stand-in ``execute_action`` that writes the runner's report pair, as a script would."""
    def execute(_actions):
        Path(f"{name}_success.json").write_text(json.dumps(success or {}), encoding="utf-8")
        Path(f"{name}_failure.json").write_text(json.dumps(failure or {}), encoding="utf-8")
    return execute


def _report() -> dict:
    return json.loads(Path("report/testpioneer-report.json").read_text(encoding="utf-8"))


class TestReportFiles:
    def test_json_and_html_are_written_by_default(self):
        result = execute_yaml(PASSING, "String")
        assert result.reports == [str(Path("report") / "testpioneer-report.json"),
                                  str(Path("report") / "testpioneer-report.html")]
        assert _report() == result.to_dict()
        assert f"Run <b>{result.run_id}</b>" in Path("report/testpioneer-report.html").read_text(encoding="utf-8")

    def test_the_workflow_chooses_formats_and_location(self):
        result = execute_yaml("report_path: out/reports\nreport_formats: [junit]\n" + PASSING, "String")
        assert result.reports == [str(Path("out/reports") / "testpioneer-junit.xml")]
        assert not Path("report").exists()
        assert ElementTree.parse("out/reports/testpioneer-junit.xml").getroot().tag == "testsuites"

    def test_the_options_override_the_workflow(self):
        options = RunOptions(report_path="chosen", report_formats=["json"])
        execute_yaml("report_path: ignored\nreport_formats: [html, junit]\n" + PASSING, "String", options)
        assert [path.name for path in Path("chosen").iterdir()] == ["testpioneer-report.json"]
        assert not Path("ignored").exists()

    def test_an_empty_list_writes_no_report(self):
        result = execute_yaml("report_formats: []\n" + PASSING, "String")
        assert result.reports == []
        assert not Path("report").exists()

    @pytest.mark.parametrize("value", ["html", "[pdf]", "[json, 5]", "5"])
    def test_an_invalid_format_list_is_refused(self, value):
        with pytest.raises(YamlException, match="report_formats must be a list of json, html, junit"):
            execute_yaml(f"report_formats: {value}\n" + PASSING, "String")

    def test_a_report_that_cannot_be_written_is_only_a_warning(self):
        Path("blocked").write_text("a file where the directory should go", encoding="utf-8")
        result = execute_yaml("report_path: blocked\n" + PASSING, "String")
        assert result.status is Status.PASSED
        assert result.reports == []
        assert len(result.warnings) == 1 and result.warnings[0].startswith("the report was not written:")

    def test_the_manifest_names_the_reports(self):
        result = execute_yaml("keep_artifacts: always\n" + PASSING, "String", RunOptions(run_id="r1"))
        manifest = json.loads(Path("artifacts/r1/testpioneer/manifest.json").read_text(encoding="utf-8"))
        assert manifest["reports"] == result.reports
        assert manifest == result.to_dict()

    def test_a_run_that_raises_still_gets_its_report(self):
        with pytest.raises(YamlException):
            execute_yaml("key: value", "String")
        assert (_report()["status"], _report()["message"]) == ("error", "YamlException('No jobs tag')")


@pytest.mark.usefixtures("script")
class TestDeclaredArtifacts:
    def test_the_runner_report_is_collected_and_read(self):
        execute = _reporting_runner({"Success_Test1": PASSED_RECORD})
        with patch(SELECT, return_value=(True, execute)):
            result = execute_yaml("keep_artifacts: always\n" + RUN_STEP, "String", RunOptions(run_id="r1"))
        (runner,) = result.runners
        assert runner.status is Status.PASSED
        assert [(case.name, case.status) for case in runner.cases] == [
            ("GET http://localhost/users", Status.PASSED)]
        assert runner.report == "runners/api-runner/01-api/collected/reports/api_run_success.json"
        assert (Path("artifacts/r1") / runner.report).is_file()
        assert result.case_summary()["passed"] == 1
        assert result.warnings == []

    def test_a_failed_test_in_the_report_fails_a_runner_that_ended_normally(self):
        execute = _reporting_runner({"Success_Test1": PASSED_RECORD}, {"Failure_Test1": FAILED_RECORD})
        with patch(SELECT, return_value=(True, execute)):
            result = execute_yaml(RUN_STEP, "String", RunOptions(run_id="r1"))
        (runner,) = result.runners
        assert (runner.status, runner.message) == (Status.FAILED, "1 of 2 recorded test(s) failed")
        assert runner.cases[0].message == "status 500"
        assert result.steps[0].status is Status.FAILED
        assert result.status is Status.FAILED
        # The run failed, so what the runner left is kept without asking for it.
        kept = [item.path for item in runner.artifacts]
        assert kept == ["runners/api-runner/01-api/collected/reports/api_run_failure.json",
                        "runners/api-runner/01-api/collected/reports/api_run_success.json"]
        assert runner.report == kept[0]

    def test_a_passed_runner_keeps_its_cases_but_not_its_files_by_default(self):
        execute = _reporting_runner({"Success_Test1": PASSED_RECORD})
        with patch(SELECT, return_value=(True, execute)):
            result = execute_yaml(RUN_STEP, "String")
        (runner,) = result.runners
        assert len(runner.cases) == 1
        assert (runner.report, runner.artifact_dir, runner.artifacts) == (None, None, [])
        assert not Path("artifacts").exists()
        assert _report()["runners"][0]["cases"] == [
            {"name": "GET http://localhost/users", "status": "passed", "message": None}]

    def test_a_report_left_by_an_earlier_run_is_not_taken_for_this_one(self):
        stale = Path("reports/api_old_failure.json")
        stale.write_text(json.dumps({"Failure_Test1": FAILED_RECORD}), encoding="utf-8")
        long_ago = time.time() - 3600
        os.utime(stale, (long_ago, long_ago))
        with patch(SELECT, return_value=(True, lambda _actions: None)):
            result = execute_yaml(RUN_STEP, "String")
        (runner,) = result.runners
        assert (runner.status, runner.cases) == (Status.PASSED, [])
        assert result.warnings == [
            "api-runner (case.json): artifact pattern 'reports/api_*.json' matched no file written by this runner"]

    def test_a_malformed_report_is_a_warning_and_the_outcome_stands(self):
        def execute(_actions):
            Path("reports/api_run_failure.json").write_text("{broken", encoding="utf-8")

        with patch(SELECT, return_value=(True, execute)):
            result = execute_yaml("keep_artifacts: always\n" + RUN_STEP, "String", RunOptions(run_id="r1"))
        (runner,) = result.runners
        assert (runner.status, runner.cases, runner.report) == (Status.PASSED, [], None)
        assert len(result.warnings) == 1
        assert result.warnings[0].startswith("api-runner (case.json): the runner report could not be read:")
        # The raw file is still there to look at.
        assert (Path("artifacts/r1/runners/api-runner/01-api/collected/reports/api_run_failure.json")).is_file()

    def test_a_pattern_that_leaves_the_working_directory_is_refused(self):
        text = RUN_STEP.replace("reports/api_*.json", "../*.json")
        with patch(SELECT, return_value=(True, lambda _actions: None)):
            result = execute_yaml(text, "String")
        assert result.status is Status.PASSED
        assert result.warnings == [
            "api-runner (case.json): artifact pattern '../*.json' is not used: it leaves the working directory"]

    def test_files_are_collected_even_when_the_runner_raises(self):
        def execute(_actions):
            Path("reports/api_run_failure.json").write_text(json.dumps({"Failure_Test1": FAILED_RECORD}),
                                                            encoding="utf-8")
            raise RuntimeError("driver crashed")

        with patch(SELECT, return_value=(True, execute)), pytest.raises(RuntimeError):
            execute_yaml(RUN_STEP, "String", RunOptions(run_id="r1"))
        runner = _report()["runners"][0]
        assert (runner["status"], runner["message"]) == ("error", "RuntimeError('driver crashed')")
        assert [case["status"] for case in runner["cases"]] == ["failed"]
        assert Path("artifacts/r1", runner["report"]).is_file()


@pytest.fixture
def fake_runner(tmp_path_factory, monkeypatch):
    """Register ``fake-runner``, whose reports name a test by its ``name`` field."""
    package = tmp_path_factory.mktemp("packages") / "fake_runner"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "__main__.py").write_text(FAKE_RUNNER, encoding="utf-8")
    monkeypatch.setenv("PYTHONPATH", str(package.parent))
    monkeypatch.setattr(registry, "RUNNERS", {
        **registry.RUNNERS,
        "fake-runner": ModuleRunner("fake-runner", "fake_runner", report=RecordPairReader(("name",))),
    })
    monkeypatch.setitem(parallel_run_module._BASE_RUNNER_COMMANDS, "fake-runner", "fake_runner")


def _plan(name: str, **plan) -> str:
    Path(name).write_text(json.dumps({"report": Path(name).stem, **plan}), encoding="utf-8")
    return name


def _parallel(*scripts: str, extra: str = "", artifacts: str = "") -> str:
    return (
        f"{extra}jobs:\n  steps:\n    - name: together\n      parallel_run:\n"
        f"        runners: {json.dumps(['fake-runner'] * len(scripts))}\n"
        f"        scripts: {json.dumps(list(scripts))}\n{artifacts}"
    )


@pytest.mark.usefixtures("fake_runner")
class TestSeveralRunners:
    def test_one_report_holds_every_runner(self):
        text = _parallel(_plan("web.json", passed=["open page", "click"]),
                         _plan("api.json", passed=["GET /users"], failed=["POST /login"]),
                         extra="report_formats: [json, html, junit]\n")
        result = execute_yaml(text, "String", RunOptions(run_id="r1"))
        web, api = result.runners
        assert (web.status, web.exit_code, len(web.cases)) == (Status.PASSED, 0, 2)
        assert (api.status, api.exit_code, api.message) == (Status.FAILED, 0, "1 of 2 recorded test(s) failed")
        assert result.status is Status.FAILED
        assert result.summary() == {"passed": 1, "failed": 1, "error": 0, "cancelled": 0, "total": 2}
        assert result.case_summary() == {"passed": 3, "failed": 1, "error": 0, "cancelled": 0, "total": 4}

        page = Path("report/testpioneer-report.html").read_text(encoding="utf-8")
        for text_in_page in ("fake-runner: web.json", "fake-runner: api.json", "POST /login", "boom"):
            assert text_in_page in page
        assert 'href="../artifacts/r1/runners/fake-runner/02-together-2/api_failure.json"' in page

        root = ElementTree.parse("report/testpioneer-junit.xml").getroot()
        assert (root.get("tests"), root.get("failures")) == ("4", "1")
        assert [suite.get("name") for suite in root] == ["fake-runner: web.json", "fake-runner: api.json"]

    def test_the_raw_report_of_the_failed_runner_is_kept_beside_the_merged_one(self):
        text = _parallel(_plan("web.json", passed=["open page"]), _plan("api.json", failed=["POST /login"]))
        result = execute_yaml(text, "String", RunOptions(run_id="r1"))
        web, api = result.runners
        assert (web.artifact_dir, web.report) == (None, None)
        assert api.report == "runners/fake-runner/02-together-2/api_failure.json"
        raw = json.loads((Path("artifacts/r1") / api.report).read_text(encoding="utf-8"))
        assert raw == {"Failure_Test1": {"name": "POST /login", "error": "boom"}}

    def test_every_runner_failing_is_reported_for_each(self):
        text = _parallel(_plan("one.json", failed=["a"]), _plan("two.json", failed=["b", "c"]))
        result = execute_yaml(text, "String")
        assert [runner.status for runner in result.runners] == [Status.FAILED, Status.FAILED]
        assert [runner.message for runner in result.runners] == [
            "1 of 1 recorded test(s) failed", "2 of 2 recorded test(s) failed"]
        assert result.case_summary()["failed"] == 3

    def test_a_malformed_report_of_one_runner_does_not_hide_the_other(self):
        text = _parallel(_plan("bad.json", raw_failure="{broken"), _plan("good.json", failed=["x"]))
        result = execute_yaml(text, "String", RunOptions(run_id="r1"))
        bad, good = result.runners
        assert (bad.status, bad.cases) == (Status.PASSED, [])
        assert (good.status, len(good.cases)) == (Status.FAILED, 1)
        assert len(result.warnings) == 1
        assert result.warnings[0].startswith("fake-runner (bad.json): the runner report could not be read:")
        assert _report()["warnings"] == result.warnings

    def test_each_entry_collects_its_own_declared_files(self):
        Path("out").mkdir()
        text = _parallel(
            _plan("web.json", passed=["open page"], write_to="out"),
            _plan("api.json", failed=["POST /login"], write_to="out"),
            extra="keep_artifacts: always\n",
            artifacts="        artifacts: [['out/web_*.json'], ['out/api_*.json']]\n")
        result = execute_yaml(text, "String", RunOptions(run_id="r1"))
        web, api = result.runners
        assert [case.name for case in web.cases] == ["open page"]
        assert [case.name for case in api.cases] == ["POST /login"]
        assert web.report == "runners/fake-runner/01-together-1/collected/out/web_success.json"
        assert api.report == "runners/fake-runner/02-together-2/collected/out/api_failure.json"
        assert result.warnings == []
