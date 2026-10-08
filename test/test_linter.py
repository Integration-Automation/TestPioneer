"""Tests for test_pioneer.validation.linter, through ``lint_yaml``."""
from pathlib import Path
from unittest.mock import patch

import pytest

from test_pioneer import lint_yaml
from test_pioneer.models.diagnostic import Severity
from test_pioneer.project.template.template import template_1_str
from test_pioneer.validation import LintOptions

REPO_ROOT = Path(__file__).resolve().parents[1]
NO_FILES = LintOptions(check_files=False)
INSTALLED = "test_pioneer.validation.linter.is_installed"
PARALLEL = "    - name: a\n      parallel_run:\n"


@pytest.fixture(autouse=True)
def every_runner_installed(monkeypatch):
    """Keep the result independent of which runner packages this machine has."""
    monkeypatch.setattr(INSTALLED, lambda package: True)


def _steps(body: str) -> str:
    """Wrap step lines (indented by four spaces) in a workflow."""
    return "jobs:\n  steps:\n" + body


def _lint(text: str, options: LintOptions = NO_FILES):
    return lint_yaml(text, "String", options).diagnostics


def _codes(text: str, options: LintOptions = NO_FILES) -> list:
    return [item.code for item in _lint(text, options)]


class TestCleanWorkflows:
    def test_project_template_has_no_problem(self):
        assert _lint(template_1_str) == ()

    @pytest.mark.parametrize("workflow", [
        "docker_gui_test/test_run_multi_time.yml",
        "docker_non_gui_test/test_run_multi_time.yml",
    ])
    def test_bundled_sample_and_its_scripts_have_no_problem(self, workflow):
        result = lint_yaml(str(REPO_ROOT / workflow), options=LintOptions(base_dir=REPO_ROOT))
        assert result.diagnostics == ()

    def test_schema_problems_are_included(self):
        assert _codes(_steps("    - name: a\n      wait: soon\n")) == ["schema-type"]

    def test_syntax_error_is_the_only_report(self):
        assert _codes("jobs:\n  steps: [1, 2\n") == ["yaml-syntax"]


class TestStepNames:
    def test_duplicate_name_is_an_error_on_the_second_step(self):
        (problem,) = _lint(_steps("    - name: dup\n      wait: 1\n    - name: dup\n      wait: 2\n"))
        assert (problem.code, problem.severity) == ("duplicate-step-name", Severity.ERROR)
        assert problem.message == "step name 'dup' is already used by jobs.steps[0]"
        assert (problem.path, problem.line, problem.column) == (("jobs", "steps", 1, "name"), 5, 13)

    def test_third_use_still_names_the_first_step(self):
        problems = _lint(_steps("    - name: n\n      wait: 1\n" * 3))
        assert [item.message for item in problems] == ["step name 'n' is already used by jobs.steps[0]"] * 2


class TestActions:
    def test_step_without_an_action(self):
        (problem,) = _lint(_steps("    - name: idle\n"))
        assert (problem.code, problem.severity) == ("missing-action", Severity.ERROR)
        assert problem.path == ("jobs", "steps", 0)

    def test_misspelled_action_is_named_and_reported_as_missing(self):
        problems = _lint(_steps("    - name: a\n      open_ulr: https://example.com\n"))
        assert [item.code for item in problems] == ["missing-action", "unknown-key"]
        assert problems[1].message == "unknown key 'open_ulr' is ignored. Did you mean 'open_url'?"
        assert problems[1].severity is Severity.WARNING

    def test_two_actions_in_one_step(self):
        (problem,) = _lint(_steps("    - name: a\n      wait: 1\n      open_url: https://example.com\n"))
        assert (problem.code, problem.severity) == ("conflicting-actions", Severity.ERROR)
        assert problem.message == "step has several action keys (open_url, wait); only 'open_url' would run"
        assert (problem.path, problem.line) == (("jobs", "steps", 0, "wait"), 4)


class TestFields:
    @pytest.mark.parametrize("body, message", [
        ("      run: a.json\n", "a 'run' step needs 'with'"),
        ("      run_folder: tests\n", "a 'run_folder' step needs 'with'"),
        ("      download_file: https://example.com/a.zip\n", "a 'download_file' step needs 'file_path'"),
        ("      unzip_zipfile: true\n", "a 'unzip_zipfile' step needs 'zip_file_path'"),
    ])
    def test_action_without_its_required_field(self, body, message):
        (problem,) = _lint(_steps("    - name: a\n" + body))
        assert (problem.code, problem.severity, problem.message) == (
            "missing-required-field", Severity.ERROR, message)
        assert (problem.line, problem.column) == (4, 7)

    def test_field_of_another_action_is_a_warning(self):
        (problem,) = _lint(_steps("    - name: a\n      wait: 1\n      with: api-runner\n"))
        assert (problem.code, problem.severity) == ("unused-field", Severity.WARNING)
        assert problem.message == "'with' has no effect on a 'wait' step"
        assert problem.path == ("jobs", "steps", 0, "with")

    def test_misspelled_field_is_named(self):
        problems = _lint(_steps("    - name: a\n      download_file: https://example.com/a\n      file_name: a\n"))
        assert [item.code for item in problems] == ["missing-required-field", "unknown-key"]
        assert problems[1].message == "unknown key 'file_name' is ignored. Did you mean 'file_path'?"


class TestUnknownKeys:
    def test_top_level_key(self):
        (problem,) = _lint("pioneer_logs: a.log\n" + _steps("    - name: a\n      wait: 1\n"))
        assert (problem.code, problem.path, problem.line, problem.column) == ("unknown-key", ("pioneer_logs",), 1, 1)
        assert problem.message.endswith("Did you mean 'pioneer_log'?")

    def test_key_under_jobs(self):
        assert _codes("jobs:\n  step: []\n  steps:\n    - name: a\n      wait: 1\n") == ["unknown-key"]

    def test_key_inside_parallel_run(self):
        body = PARALLEL + "        runners: [api-runner]\n        scripts: [a.json]\n        timeout: 5\n"
        (problem,) = _lint(_steps(body))
        assert (problem.code, problem.path) == ("unknown-key", ("jobs", "steps", 0, "parallel_run", "timeout"))


class TestParallelRun:
    def test_more_runners_than_scripts(self):
        body = PARALLEL + "        runners: [api-runner, web-runner]\n        scripts: [a.json]\n"
        (problem,) = _lint(_steps(body))
        assert (problem.code, problem.severity) == ("runners-scripts-mismatch", Severity.ERROR)
        assert problem.message == "'runners' has 2 entries and 'scripts' has 1; they are paired one to one"
        assert (problem.line, problem.column) == (4, 7)

    def test_matching_lengths(self):
        body = PARALLEL + "        runners: [api-runner, web-runner]\n        scripts: [a.json, b.json]\n"
        assert _codes(_steps(body)) == []


class TestArtifacts:
    def test_declared_artifacts_are_fine_on_runner_steps(self):
        body = (
            "    - name: one\n      run: a.json\n      with: api-runner\n      artifacts: ['reports/*.json']\n"
            "    - name: all\n      run_folder: cases\n      with: api-runner\n      artifacts: [shots]\n"
            + PARALLEL.replace("name: a", "name: both")
            + "        runners: [api-runner, web-runner]\n        scripts: [a.json, b.json]\n"
            "        artifacts: [['reports/a_*.json'], []]\n"
        )
        assert _codes(_steps(body)) == []

    def test_artifacts_on_a_step_without_a_runner_have_no_effect(self):
        (problem,) = _lint(_steps("    - name: a\n      wait: 1\n      artifacts: [shots]\n"))
        assert (problem.code, problem.message) == ("unused-field", "'artifacts' has no effect on a 'wait' step")

    @pytest.mark.parametrize("pattern, reason", [
        ("../reports/*.json", "it leaves the working directory"),
        ("/var/reports", "it is not relative to the working directory"),
    ])
    def test_a_pattern_that_would_be_refused_is_a_warning(self, pattern, reason):
        body = f"    - name: a\n      run: a.json\n      with: api-runner\n      artifacts: [ok, '{pattern}']\n"
        (problem,) = _lint(_steps(body))
        assert (problem.code, problem.severity) == ("artifact-pattern", Severity.WARNING)
        assert problem.message == f"artifact pattern '{pattern}' is not used: {reason}"
        assert problem.path == ("jobs", "steps", 0, "artifacts", 1)

    def test_parallel_artifacts_and_scripts_of_different_lengths(self):
        body = PARALLEL + (
            "        runners: [api-runner, web-runner]\n        scripts: [a.json, b.json]\n"
            "        artifacts: [['reports/*.json']]\n")
        (problem,) = _lint(_steps(body))
        assert (problem.code, problem.severity) == ("artifacts-scripts-mismatch", Severity.ERROR)
        assert problem.message == (
            "'artifacts' has 1 entries and 'scripts' has 2; each script has its own list of patterns")
        assert (problem.line, problem.column) == (7, 9)

    def test_a_refused_pattern_inside_parallel_run(self):
        body = PARALLEL + (
            "        runners: [api-runner]\n        scripts: [a.json]\n        artifacts: [['../x']]\n")
        (problem,) = _lint(_steps(body))
        assert (problem.code, problem.path) == (
            "artifact-pattern", ("jobs", "steps", 0, "parallel_run", "artifacts", 0, 0))


class TestRunnerPackages:
    @patch(INSTALLED, return_value=False)
    def test_missing_gui_package_is_reported_once_with_the_extra(self, _installed):
        body = (
            "    - name: a\n      run: a.json\n      with: gui-runner\n"
            "    - name: b\n      run: b.json\n      with: gui-runner\n"
        )
        (problem,) = _lint(_steps(body))
        assert (problem.code, problem.severity) == ("runner-not-installed", Severity.WARNING)
        assert problem.message == (
            "'gui-runner' needs the 'je_auto_control' package, which is not installed here."
            " Install it with: pip install test_pioneer[gui]")
        assert problem.path == ("jobs", "steps", 0, "with")

    @patch(INSTALLED, return_value=False)
    def test_missing_core_package_in_parallel_run(self, _installed):
        body = "    - name: a\n      parallel_run:\n        runners: [api-runner]\n        scripts: [a.json]\n"
        (problem,) = _lint(_steps(body))
        assert problem.message == "'api-runner' needs the 'je_api_testka' package, which is not installed here."
        assert problem.path == ("jobs", "steps", 0, "parallel_run", "runners", 0)

    @patch(INSTALLED, return_value=False)
    def test_unknown_runner_is_left_to_the_schema(self, _installed):
        assert _codes(_steps("    - name: a\n      run: a.json\n      with: cli-runner\n")) == ["schema-enum"]


class TestPrograms:
    def test_closing_an_opened_program(self):
        body = "    - name: app\n      open_program: app.exe\n    - name: stop\n      close_program: app\n"
        assert _codes(_steps(body)) == []

    def test_closing_a_program_that_was_never_opened(self):
        (problem,) = _lint(_steps("    - name: stop\n      close_program: app\n"))
        assert (problem.code, problem.severity) == ("unknown-program", Severity.WARNING)
        assert problem.message == "no open_program step named 'app' is open at this point"

    def test_closing_a_program_before_it_is_opened(self):
        body = "    - name: stop\n      close_program: app\n    - name: app\n      open_program: app.exe\n"
        assert _codes(_steps(body)) == ["unknown-program"]

    def test_closing_a_program_twice(self):
        body = (
            "    - name: app\n      open_program: app.exe\n"
            "    - name: stop\n      close_program: app\n"
            "    - name: again\n      close_program: app\n"
        )
        assert [item.path for item in _lint(_steps(body))] == [("jobs", "steps", 2, "close_program")]


class TestFiles:
    def test_existing_script_folder_and_parallel_scripts(self, tmp_path):
        (tmp_path / "cases").mkdir()
        (tmp_path / "cases" / "a.json").write_text("[]", encoding="utf-8")
        body = (
            "    - name: one\n      run: cases/a.json\n      with: api-runner\n"
            "    - name: all\n      run_folder: cases\n      with: api-runner\n"
            "    - name: both\n      parallel_run:\n        runners: [api-runner]\n        scripts: [./cases/a.json]\n"
        )
        assert _codes(_steps(body), LintOptions(base_dir=tmp_path)) == []

    def test_missing_script(self, tmp_path):
        (problem,) = _lint(_steps("    - name: a\n      run: absent.json\n      with: api-runner\n"),
                           LintOptions(base_dir=tmp_path))
        assert (problem.code, problem.severity) == ("missing-file", Severity.WARNING)
        assert problem.message == f"file not found: absent.json (looked in {tmp_path.resolve()})"
        assert problem.path == ("jobs", "steps", 0, "run")

    def test_missing_folder(self, tmp_path):
        (problem,) = _lint(_steps("    - name: a\n      run_folder: absent\n      with: api-runner\n"),
                           LintOptions(base_dir=tmp_path))
        assert problem.message.startswith("folder not found: absent")

    def test_folder_without_json(self, tmp_path):
        (tmp_path / "empty").mkdir()
        (problem,) = _lint(_steps("    - name: a\n      run_folder: empty\n      with: api-runner\n"),
                           LintOptions(base_dir=tmp_path))
        assert problem.message.startswith("folder has no .json file: empty")

    def test_missing_parallel_script(self, tmp_path):
        body = "    - name: a\n      parallel_run:\n        runners: [api-runner]\n        scripts: [absent.json]\n"
        (problem,) = _lint(_steps(body), LintOptions(base_dir=tmp_path))
        assert (problem.code, problem.path) == ("missing-file", ("jobs", "steps", 0, "parallel_run", "scripts", 0))

    def test_absolute_path_ignores_the_base_directory(self, tmp_path):
        script = tmp_path / "abs.json"
        script.write_text("[]", encoding="utf-8")
        body = f"    - name: a\n      run: '{script.as_posix()}'\n      with: api-runner\n"
        assert _codes(_steps(body), LintOptions(base_dir=tmp_path / "elsewhere")) == []

    def test_file_check_can_be_turned_off(self, tmp_path):
        body = "    - name: a\n      run: absent.json\n      with: api-runner\n"
        assert _codes(_steps(body), LintOptions(base_dir=tmp_path, check_files=False)) == []

    def test_base_directory_defaults_to_the_working_directory(self, tmp_path, monkeypatch):
        (tmp_path / "here.json").write_text("[]", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        assert _codes(_steps("    - name: a\n      run: here.json\n      with: api-runner\n"), LintOptions()) == []

    def test_script_downloaded_by_an_earlier_step_is_not_missing(self, tmp_path):
        body = (
            "    - name: get\n      download_file: https://example.com/a.json\n      file_path: fetched/a.json\n"
            "    - name: use\n      run: fetched/a.json\n      with: api-runner\n"
        )
        assert _codes(_steps(body), LintOptions(base_dir=tmp_path)) == []

    def test_script_unzipped_by_an_earlier_step_is_not_missing(self, tmp_path):
        body = (
            "    - name: unpack\n      unzip_zipfile: true\n      zip_file_path: a.zip\n      extract_path: unpacked\n"
            "    - name: use\n      run_folder: unpacked/cases\n      with: api-runner\n"
            "    - name: other\n      run: elsewhere/a.json\n      with: api-runner\n"
        )
        assert [item.path for item in _lint(_steps(body), LintOptions(base_dir=tmp_path))] == [
            ("jobs", "steps", 2, "run")]

    def test_unzip_into_the_working_directory_may_create_anything_below_it(self, tmp_path):
        body = (
            "    - name: unpack\n      unzip_zipfile: true\n      zip_file_path: a.zip\n"
            "    - name: use\n      run: cases/a.json\n      with: api-runner\n"
        )
        assert _codes(_steps(body), LintOptions(base_dir=tmp_path)) == []

    def test_script_used_before_it_is_downloaded_is_missing(self, tmp_path):
        body = (
            "    - name: use\n      run: fetched/a.json\n      with: api-runner\n"
            "    - name: get\n      download_file: https://example.com/a.json\n      file_path: fetched/a.json\n"
        )
        assert _codes(_steps(body), LintOptions(base_dir=tmp_path)) == ["missing-file"]


class TestMalformedInput:
    @pytest.mark.parametrize("text", [
        "- a\n- b\n",
        "jobs: 5\n",
        "jobs:\n  steps: nope\n",
        "jobs:\n  steps:\n    - just text\n    - 5\n",
        "jobs:\n  steps:\n    - name: a\n      parallel_run: nope\n",
        "jobs:\n  steps:\n    - name: a\n      parallel_run:\n        runners: nope\n        scripts: [a.json]\n",
        "jobs:\n  steps:\n    - name: [a]\n      close_program: [b]\n",
        "jobs:\n  steps:\n    - name: a\n      run: [a.json]\n      with: [api-runner]\n",
    ])
    def test_wrong_shapes_are_reported_by_the_schema_only(self, text):
        problems = _lint(text)
        assert problems != ()
        assert {item.source for item in problems} == {"schema"}
