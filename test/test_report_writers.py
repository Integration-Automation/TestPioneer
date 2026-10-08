"""Tests for the consolidated report: JSON, HTML and JUnit XML."""
import json
from pathlib import Path
from xml.etree import ElementTree  # nosec B405  # nosemgrep  # parses only XML written by this test

import pytest

from test_pioneer.models.result import Artifact, CaseResult, RunnerResult, RunResult, Status, StepResult
from test_pioneer.report.html_report import render_html
from test_pioneer.report.junit_report import render_junit
from test_pioneer.report.service import write_reports


def _result() -> RunResult:
    """A failed run: an API runner with one failed test, a web runner that passed, a failed download."""
    api = RunnerResult(
        "api-runner", "tests/api.json", "parallel_tests", Status.FAILED, exit_code=0, duration_ms=1500,
        started_at="2026-10-08T03:15:42.131Z", message="1 of 2 recorded test(s) failed",
        artifact_dir="runners/api-runner/01-parallel_tests-1",
        report="runners/api-runner/01-parallel_tests-1/collected/api_failure.json",
        artifacts=[
            Artifact("runners/api-runner/01-parallel_tests-1/collected/api_failure.json", "report", 120),
            Artifact("runners/api-runner/01-parallel_tests-1/stdout.log", "log", 40),
        ],
        cases=[CaseResult("post http://localhost/login", Status.FAILED, "status_code 500 != 200"),
               CaseResult("GET http://localhost/users", Status.PASSED)],
    )
    web = RunnerResult("web-runner", "tests/web.json", "parallel_tests", Status.PASSED, exit_code=0, duration_ms=900)
    return RunResult(
        run_id="r1", status=Status.FAILED, started_at="2026-10-08T03:15:42.105Z", duration_ms=7766,
        workflow="tests/test.yaml", artifact_dir=str(Path("artifacts") / "r1"),
        steps=[StepResult("parallel_tests", "parallel_run", Status.FAILED, duration_ms=1600, message="api failed"),
               StepResult("download_asset", "download_file", Status.FAILED, duration_ms=30, message="404"),
               StepResult("later", "wait", Status.CANCELLED)],
        runners=[api, web], warnings=["artifact pattern 'x' matched no file written by this runner"],
    )


class TestWriteReports:
    def test_each_format_has_its_file(self, tmp_path):
        written = write_reports(_result(), tmp_path / "report", ["json", "html", "junit"])
        assert [path.name for path in written] == [
            "testpioneer-report.json", "testpioneer-report.html", "testpioneer-junit.xml"]
        assert all(path.is_file() for path in written)

    def test_the_json_report_is_the_result_and_names_every_report(self, tmp_path):
        result = _result()
        written = write_reports(result, tmp_path / "report", ["json", "html"])
        payload = json.loads(written[0].read_text(encoding="utf-8"))
        assert payload == result.to_dict()
        assert payload["reports"] == [str(path) for path in written]
        assert payload["cases"] == {"passed": 1, "failed": 1, "error": 0, "cancelled": 0, "total": 2}

    def test_a_format_named_twice_is_written_once(self, tmp_path):
        assert len(write_reports(_result(), tmp_path, ["json", "json"])) == 1

    def test_no_format_writes_nothing(self, tmp_path):
        result = _result()
        assert write_reports(result, tmp_path / "report", []) == []
        assert not (tmp_path / "report").exists()
        assert result.reports == []

    def test_an_unknown_format_is_refused_before_anything_is_written(self, tmp_path):
        result = _result()
        with pytest.raises(ValueError, match="unknown report format: pdf"):
            write_reports(result, tmp_path / "report", ["json", "pdf"])
        assert not (tmp_path / "report").exists()

    def test_text_outside_utf8_does_not_stop_the_report(self, tmp_path):
        result = _result()
        result.steps[0].message = "lone surrogate \udc80"
        written = write_reports(result, tmp_path, ["json", "html", "junit"])
        assert "\\udc80" in written[1].read_text(encoding="utf-8")


class TestHtml:
    def test_the_page_shows_the_run_the_steps_and_the_runners(self, tmp_path):
        page = render_html(_result(), tmp_path / "report")
        assert page.startswith("<!DOCTYPE html>")
        assert "Run <b>r1</b>" in page
        assert "tests/test.yaml" in page
        for text in ("parallel_tests", "download_asset", "api-runner: tests/api.json",
                     "web-runner: tests/web.json", "post http://localhost/login", "status_code 500 != 200",
                     "1 of 2 recorded test(s) failed", "exit code 0"):
            assert text in page
        assert page.count('class="badge failed"') >= 3
        assert "Warning: artifact pattern &#x27;x&#x27; matched no file written by this runner" in page

    def test_the_tiles_count_runners_and_recorded_tests(self, tmp_path):
        page = render_html(_result(), tmp_path)
        assert "Runner executions</span><b>2</b>1 passed, 1 failed" in page
        assert "Recorded tests</span><b>2</b>1 passed, 1 failed" in page

    def test_artifacts_are_linked_relative_to_the_page(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        page = render_html(_result(), Path("report"))
        assert ('<a href="../artifacts/r1/runners/api-runner/01-parallel_tests-1/stdout.log">stdout.log</a>'
                in page)
        assert "api_failure.json</a> <span class=\"muted\">report, 120 bytes (runner report)</span>" in page

    def test_a_run_without_kept_artifacts_has_no_links(self, tmp_path):
        result = _result()
        result.artifact_dir = None
        page = render_html(result, tmp_path)
        assert "<a href" not in page
        assert "stdout.log" in page

    def test_markup_in_names_and_messages_is_escaped(self, tmp_path):
        result = _result()
        result.steps[0].name = "<script>alert(1)</script>"
        result.runners[0].cases = [CaseResult('"><img src=x onerror=alert(1)>', Status.FAILED, "<b>bold</b>")]
        result.workflow = "a&b.yml"
        page = render_html(result, tmp_path)
        assert "<script>" not in page
        assert "<img" not in page
        assert "<b>bold</b>" not in page
        assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
        assert "a&amp;b.yml" in page

    def test_special_characters_in_a_link_are_quoted(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = _result()
        result.runners[0].artifacts = [Artifact('runners/api-runner/01/a b"c.log', "log", 1)]
        page = render_html(result, Path("report"))
        assert 'href="../artifacts/r1/runners/api-runner/01/a%20b%22c.log"' in page

    def test_a_long_list_of_passed_tests_is_folded(self, tmp_path):
        result = _result()
        result.runners[0].cases = [CaseResult(f"case {index}", Status.PASSED) for index in range(25)]
        page = render_html(result, tmp_path)
        assert "<summary>5 more passed</summary>" in page

    def test_a_run_without_runners_says_so(self, tmp_path):
        page = render_html(RunResult(run_id="r1", message="No jobs tag", status=Status.ERROR), tmp_path)
        assert '<p class="muted">None.</p>' in page
        assert "No jobs tag" in page
        assert "inline YAML" in page

    def test_the_page_loads_nothing_and_runs_no_script(self, tmp_path):
        page = render_html(_result(), tmp_path)
        assert "<script" not in page
        assert "http://" not in page.replace("http://localhost", "")
        assert "https://" not in page


class TestJUnit:
    def test_the_document_is_well_formed_and_counts_every_test(self):
        root = ElementTree.fromstring(render_junit(_result()))
        assert root.tag == "testsuites"
        assert (root.get("tests"), root.get("failures"), root.get("errors")) == ("5", "2", "0")
        assert root.get("time") == "7.766"
        assert [suite.get("name") for suite in root] == [
            "api-runner: tests/api.json", "web-runner: tests/web.json", "workflow steps"]

    def test_a_runner_with_a_report_lists_its_recorded_tests(self):
        api = ElementTree.fromstring(render_junit(_result()))[0]
        assert (api.get("tests"), api.get("failures"), api.get("time")) == ("2", "1", "1.500")
        failed, passed = api
        assert (failed.get("classname"), failed.get("name")) == ("api-runner", "post http://localhost/login")
        assert failed[0].tag == "failure"
        assert failed[0].get("message") == "status_code 500 != 200"
        assert len(passed) == 0

    def test_a_runner_without_a_report_is_one_test(self):
        web = ElementTree.fromstring(render_junit(_result()))[1]
        (case,) = web
        assert (case.get("name"), case.get("time"), len(case)) == ("tests/web.json", "0.900", 0)

    def test_steps_that_are_not_runner_steps_are_tests_too(self):
        steps = ElementTree.fromstring(render_junit(_result()))[2]
        assert [(case.get("name"), case[0].tag if len(case) else None) for case in steps] == [
            ("download_asset", "failure"), ("later", "skipped")]
        assert (steps.get("failures"), steps.get("skipped")) == ("1", "1")

    def test_an_error_is_an_error_element(self):
        result = RunResult(run_id="r1", status=Status.ERROR, runners=[
            RunnerResult("api-runner", "absent.json", "api", Status.ERROR, message="Script file does not exist")])
        root = ElementTree.fromstring(render_junit(result))
        assert root.get("errors") == "1"
        assert root[0][0][0].tag == "error"

    def test_a_run_level_failure_is_a_test(self):
        result = RunResult(run_id="r1", status=Status.ERROR, message="No jobs tag")
        root = ElementTree.fromstring(render_junit(result))
        (case,) = root[0]
        assert (case.get("name"), case[0].tag, case[0].get("message")) == ("workflow", "error", "No jobs tag")

    def test_markup_and_control_characters_cannot_break_the_document(self):
        result = _result()
        result.runners[0].cases = [CaseResult('a "quoted" <tag> & more', Status.FAILED, "bell \x07 and ]]> end")]
        root = ElementTree.fromstring(render_junit(result))
        case = root[0][0]
        assert case.get("name") == 'a "quoted" <tag> & more'
        assert case[0].get("message") == "bell ? and ]]> end"

    def test_a_run_with_nothing_in_it_is_still_a_document(self):
        root = ElementTree.fromstring(render_junit(RunResult(run_id="r1")))
        assert (root.get("tests"), len(root)) == ("0", 0)
