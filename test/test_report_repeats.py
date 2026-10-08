"""A record is counted only for the in-process runner call that produced it."""
import json
from pathlib import Path
from unittest.mock import patch

from test_pioneer import execute_yaml
from test_pioneer.models.result import Status
from test_pioneer.report.readers import RecordPairReader
from test_pioneer.report.repeats import RepeatFilter

SELECT = "test_pioneer.executor.run.executor_run.select_with_runner"
READER = RecordPairReader(("name",))
TWO_STEPS = (
    "jobs:\n  steps:\n"
    "    - name: first\n      run: case.json\n      with: api-runner\n      artifacts: ['reports/first_*.json']\n"
    "    - name: second\n      run: case.json\n      with: api-runner\n      artifacts: ['reports/second_*.json']\n"
)


def _report(directory: Path, passed: list, failed: list):
    """Write a report pair as a runner would and read it back."""
    directory.mkdir(parents=True, exist_ok=True)
    success = {f"Success_Test{index}": record for index, record in enumerate(passed, 1)}
    failure = {f"Failure_Test{index}": record for index, record in enumerate(failed, 1)}
    (directory / "r_success.json").write_text(json.dumps(success), encoding="utf-8")
    (directory / "r_failure.json").write_text(json.dumps(failure), encoding="utf-8")
    return READER.read(directory)


def _names(cases: list) -> list:
    return [(case.name, case.status.value) for case in cases]


class TestRepeatFilter:
    def test_the_first_report_is_all_new(self, tmp_path):
        report = _report(tmp_path, [{"name": "a", "time": "1"}], [{"name": "x", "time": "2", "error": "boom"}])
        assert _names(RepeatFilter().new_cases("api-runner", report)) == [("x", "failed"), ("a", "passed")]

    def test_a_later_report_only_adds_what_follows_the_earlier_records(self, tmp_path):
        records = RepeatFilter()
        a, b = {"name": "a", "time": "1"}, {"name": "b", "time": "2"}
        x, y = {"name": "x", "time": "3", "error": "boom"}, {"name": "y", "time": "4", "error": "bang"}
        records.new_cases("api-runner", _report(tmp_path / "1", [a], [x]))
        second = records.new_cases("api-runner", _report(tmp_path / "2", [a, b], [x, y]))
        assert _names(second) == [("y", "failed"), ("b", "passed")]

    def test_an_earlier_failure_is_not_blamed_on_the_next_call(self, tmp_path):
        records = RepeatFilter()
        x = {"name": "x", "time": "1", "error": "boom"}
        records.new_cases("api-runner", _report(tmp_path / "1", [], [x]))
        second = records.new_cases("api-runner", _report(tmp_path / "2", [{"name": "a", "time": "2"}], [x]))
        assert _names(second) == [("a", "passed")]

    def test_a_report_with_nothing_new_has_no_case(self, tmp_path):
        records = RepeatFilter()
        a = {"name": "a", "time": "1"}
        records.new_cases("api-runner", _report(tmp_path / "1", [a], []))
        assert records.new_cases("api-runner", _report(tmp_path / "2", [a], [])) == []

    def test_identical_records_are_told_apart_by_their_number(self, tmp_path):
        # Load records carry no time, so every request to one URL looks the same.
        records = RepeatFilter()
        same = {"Method": "GET", "name": "home", "status_code": "200"}
        records.new_cases("load-runner", _report(tmp_path / "1", [same] * 3, []))
        assert len(records.new_cases("load-runner", _report(tmp_path / "2", [same] * 5, []))) == 2

    def test_cleared_records_make_every_record_new_again(self, tmp_path):
        records = RepeatFilter()
        records.new_cases("api-runner", _report(tmp_path / "1", [{"name": "a", "time": "1"}], []))
        after_clear = _report(tmp_path / "2", [{"name": "b", "time": "2"}], [])
        assert _names(records.new_cases("api-runner", after_clear)) == [("b", "passed")]
        # The cleared list is what later reports continue from.
        grown = _report(tmp_path / "3", [{"name": "b", "time": "2"}, {"name": "c", "time": "3"}], [])
        assert _names(records.new_cases("api-runner", grown)) == [("c", "passed")]

    def test_each_runner_has_its_own_records(self, tmp_path):
        records = RepeatFilter()
        a = {"name": "a", "time": "1"}
        records.new_cases("api-runner", _report(tmp_path / "1", [a], []))
        assert len(records.new_cases("web-runner", _report(tmp_path / "2", [a], []))) == 1

    def test_reset_forgets_every_report(self, tmp_path):
        records = RepeatFilter()
        a = {"name": "a", "time": "1"}
        records.new_cases("api-runner", _report(tmp_path / "1", [a], []))
        records.reset()
        assert len(records.new_cases("api-runner", _report(tmp_path / "2", [a], []))) == 1


def _accumulating_runner():
    """Stand in for a runner whose record list grows with every call in this process."""
    passed, failed, calls = [], [], []

    def execute(_actions):
        calls.append(None)
        name = "first" if len(calls) == 1 else "second"
        if name == "first":
            failed.append({"http_method": "get", "test_url": "http://localhost/broken", "error": "status 500"})
        passed.append({"request_method": "GET", "request_url": f"http://localhost/{name}"})
        success = {f"Success_Test{index}": record for index, record in enumerate(passed, 1)}
        failure = {f"Failure_Test{index}": record for index, record in enumerate(failed, 1)}
        Path(f"reports/{name}_success.json").write_text(json.dumps(success), encoding="utf-8")
        Path(f"reports/{name}_failure.json").write_text(json.dumps(failure), encoding="utf-8")
    return execute


def test_two_in_process_steps_of_one_runner_each_count_their_own_records():
    Path("case.json").write_text("[]", encoding="utf-8")
    Path("reports").mkdir()
    with patch(SELECT, return_value=(True, _accumulating_runner())):
        result = execute_yaml(TWO_STEPS, "String")
    first, second = result.runners
    assert _names(first.cases) == [("get http://localhost/broken", "failed"), ("GET http://localhost/first", "passed")]
    assert _names(second.cases) == [("GET http://localhost/second", "passed")]
    assert (first.status, second.status) == (Status.FAILED, Status.PASSED)
    assert [step.status for step in result.steps] == [Status.FAILED, Status.PASSED]
    assert result.case_summary() == {"passed": 2, "failed": 1, "error": 0, "cancelled": 0, "total": 3}


def test_a_second_run_in_the_same_process_does_not_repeat_the_first():
    Path("case.json").write_text("[]", encoding="utf-8")
    Path("reports").mkdir()
    one_step = TWO_STEPS.split("    - name: second")[0]
    with patch(SELECT, return_value=(True, _accumulating_runner())):
        first_run = execute_yaml(one_step, "String")
        second_run = execute_yaml(one_step.replace("first", "second"), "String")
    assert first_run.case_summary()["total"] == 2
    assert _names(second_run.runners[0].cases) == [("GET http://localhost/second", "passed")]
    assert second_run.status is Status.PASSED
