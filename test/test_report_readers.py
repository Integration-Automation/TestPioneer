"""Tests for test_pioneer.report.readers: runner reports become TestPioneer test cases."""
import json

import pytest

from test_pioneer.models.result import CaseResult, Status
from test_pioneer.report import readers
from test_pioneer.report.readers import ACTION_REPORT, API_REPORT, LOAD_REPORT, RecordPairReader
from test_pioneer.runner.registry import RUNNERS

# One record of each runner's report, with the field names that runner writes.
API_SUCCESS = {"Success_Test1": {
    "status_code": "200", "text": "ok", "request_method": "GET", "request_url": "http://localhost/users",
    "request_time_sec": "0.01"}}
API_FAILURE = {"Failure_Test1": {
    "http_method": "post", "test_url": "http://localhost/login", "soap": "False",
    "result_check_dict": "{'status_code': 200}", "error": "APIAssertException('status_code 500 != 200')"}}
WEB_SUCCESS = {"Success_Test1": {
    "function_name": "webdriver wrapper to_url", "param": "{'url': 'http://localhost'}",
    "time": "2026-10-08 03:15:42", "exception": "None"}}
WEB_FAILURE = {"Failure_Test1": {
    "function_name": "web element click", "param": "{'password': 'hunter2'}",
    "time": "2026-10-08 03:15:43", "exception": "NoSuchElementException('no such element')"}}
LOAD_SUCCESS = {"Success_Test1": {
    "Method": "GET", "test_url": "http://localhost/", "name": "home", "status_code": "200", "text": "<html>"}}
LOAD_FAILURE = {"Failure_Test1": {
    "Method": "GET", "test_url": "http://localhost/slow", "name": "slow", "status_code": "None",
    "error": "ConnectionError('refused')"}}


def _report(directory, name: str, success: dict | None = None, failure: dict | None = None) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if success is not None:
        (directory / f"{name}_success.json").write_text(json.dumps(success), encoding="utf-8")
    if failure is not None:
        (directory / f"{name}_failure.json").write_text(json.dumps(failure), encoding="utf-8")


class TestRunnerFormats:
    def test_api_report(self, tmp_path):
        _report(tmp_path, "api", API_SUCCESS, API_FAILURE)
        parsed = API_REPORT.read(tmp_path)
        assert parsed.cases == [
            CaseResult("post http://localhost/login", Status.FAILED, "APIAssertException('status_code 500 != 200')"),
            CaseResult("GET http://localhost/users", Status.PASSED),
        ]
        assert parsed.source == tmp_path / "api_failure.json"

    def test_web_and_gui_report_leaves_the_parameters_out(self, tmp_path):
        _report(tmp_path, "web", WEB_SUCCESS, WEB_FAILURE)
        parsed = ACTION_REPORT.read(tmp_path)
        assert parsed.cases == [
            CaseResult("web element click", Status.FAILED, "NoSuchElementException('no such element')"),
            CaseResult("webdriver wrapper to_url", Status.PASSED),
        ]
        assert "hunter2" not in repr(parsed.cases)

    def test_load_report(self, tmp_path):
        _report(tmp_path, "load", LOAD_SUCCESS, LOAD_FAILURE)
        assert LOAD_REPORT.read(tmp_path).cases == [
            CaseResult("GET slow", Status.FAILED, "ConnectionError('refused')"),
            CaseResult("GET home", Status.PASSED),
        ]

    def test_each_reporting_runner_has_a_reader(self):
        assert {name: runner.report for name, runner in RUNNERS.items()} == {
            "gui-runner": ACTION_REPORT, "web-runner": ACTION_REPORT, "api-runner": API_REPORT,
            "load-runner": LOAD_REPORT, "file-runner": None,
        }


class TestLayout:
    def test_no_report_files_means_no_report(self, tmp_path):
        (tmp_path / "stdout.log").write_text("nothing here", encoding="utf-8")
        (tmp_path / "other.json").write_text("{}", encoding="utf-8")
        assert API_REPORT.read(tmp_path) is None

    def test_reports_are_found_in_sub_directories(self, tmp_path):
        _report(tmp_path / "collected" / "reports", "api", API_SUCCESS)
        parsed = API_REPORT.read(tmp_path)
        assert [case.status for case in parsed.cases] == [Status.PASSED]
        assert parsed.source == tmp_path / "collected" / "reports" / "api_success.json"

    def test_an_empty_failure_file_leaves_the_success_file_as_the_source(self, tmp_path):
        _report(tmp_path, "api", API_SUCCESS, {})
        parsed = API_REPORT.read(tmp_path)
        assert [case.status for case in parsed.cases] == [Status.PASSED]
        assert parsed.source == tmp_path / "api_success.json"

    def test_a_failure_file_alone_is_read(self, tmp_path):
        _report(tmp_path, "api", failure=API_FAILURE)
        parsed = API_REPORT.read(tmp_path)
        assert [case.status for case in parsed.cases] == [Status.FAILED]
        assert parsed.source == tmp_path / "api_failure.json"

    def test_several_pairs_are_merged(self, tmp_path):
        _report(tmp_path, "first", API_SUCCESS, API_FAILURE)
        _report(tmp_path, "second", API_SUCCESS)
        statuses = [case.status for case in API_REPORT.read(tmp_path).cases]
        assert statuses == [Status.FAILED, Status.PASSED, Status.PASSED]


class TestRecords:
    def test_a_record_without_a_name_field_is_named_by_its_key(self, tmp_path):
        _report(tmp_path, "x", {"Success_Test7": {"unrelated": "value"}})
        assert RecordPairReader(("name",)).read(tmp_path).cases == [CaseResult("Success_Test7", Status.PASSED)]

    def test_the_first_message_field_that_has_a_value_is_used(self, tmp_path):
        _report(tmp_path, "x", failure={"Failure_Test1": {"name": "n", "error": "None", "exception": "boom"}})
        assert RecordPairReader(("name",)).read(tmp_path).cases == [CaseResult("n", Status.FAILED, "boom")]

    def test_a_failure_without_a_reason_has_no_message(self, tmp_path):
        _report(tmp_path, "x", failure={"Failure_Test1": {"name": "n"}})
        assert RecordPairReader(("name",)).read(tmp_path).cases == [CaseResult("n", Status.FAILED, None)]

    def test_long_names_and_messages_are_shortened(self, tmp_path):
        _report(tmp_path, "x", failure={"Failure_Test1": {"name": "n" * 5000, "error": "e" * 50000}})
        (case,) = RecordPairReader(("name",)).read(tmp_path).cases
        assert len(case.name) == 203
        assert len(case.message) == 2003


class TestMalformedReports:
    def test_text_that_is_not_json(self, tmp_path):
        (tmp_path / "x_failure.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(ValueError):
            API_REPORT.read(tmp_path)

    def test_a_report_that_is_a_list(self, tmp_path):
        (tmp_path / "x_success.json").write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(ValueError, match="x_success.json is not a JSON object"):
            API_REPORT.read(tmp_path)

    def test_a_record_that_is_not_an_object(self, tmp_path):
        (tmp_path / "x_success.json").write_text('{"Success_Test1": "text"}', encoding="utf-8")
        with pytest.raises(ValueError, match="Success_Test1 is not a record"):
            API_REPORT.read(tmp_path)

    def test_a_report_beyond_the_size_limit_is_not_read(self, tmp_path, monkeypatch):
        _report(tmp_path, "x", API_SUCCESS)
        monkeypatch.setattr(readers, "MAX_REPORT_BYTES", 10)
        with pytest.raises(ValueError, match="x_success.json is larger than 10 bytes"):
            API_REPORT.read(tmp_path)
