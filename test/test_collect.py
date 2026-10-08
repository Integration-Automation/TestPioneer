"""Tests for test_pioneer.artifacts.collect: copying declared files into a runner's directory."""
import os
import time
from pathlib import Path

import pytest

from test_pioneer.artifacts.collect import as_patterns, collect_files, pattern_refusal

NOW = time.time()


@pytest.fixture
def runner_dir(tmp_path):
    """A runner directory laid out as in a run: ``<run>/runners/<runner>/<nn>-<step>``."""
    directory = tmp_path / "artifacts" / "run-1" / "runners" / "api-runner" / "01-api"
    directory.mkdir(parents=True)
    return directory


def _write(name: str, text: str = "x", age: float = 0) -> Path:
    """Create a file below the working directory, optionally with an older modification time."""
    path = Path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if age:
        os.utime(path, (NOW - age, NOW - age))
    return path


def _collected(runner_dir: Path) -> list:
    root = runner_dir / "collected"
    return sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())


class TestPatterns:
    def test_a_list_of_text_is_taken_as_patterns(self):
        assert as_patterns(["a/*.json", "shots"]) == ("a/*.json", "shots")

    @pytest.mark.parametrize("value", [None, "a/*.json", ["a", 5], {"a": 1}, 3])
    def test_anything_else_is_no_pattern(self, value):
        assert as_patterns(value) == ()

    @pytest.mark.parametrize("pattern", ["reports/*.json", "shots", "**/*.png", "a.b/c"])
    def test_relative_patterns_are_accepted(self, pattern):
        assert pattern_refusal(pattern) is None

    @pytest.mark.parametrize("pattern, reason", [
        ("", "it is empty"),
        ("  ", "it is empty"),
        ("../other/*.json", "it leaves the working directory"),
        ("reports/../../x", "it leaves the working directory"),
        ("/etc/passwd", "it is not relative to the working directory"),
        ("\\\\server\\share\\x", "it is not relative to the working directory"),
        ("C:/Windows/*.ini", "it is not relative to the working directory"),
    ])
    def test_patterns_that_leave_the_working_directory_are_refused(self, pattern, reason):
        assert pattern_refusal(pattern) == reason


class TestCollect:
    def test_matching_files_are_copied_with_their_relative_path(self, runner_dir):
        _write("reports/api_success.json", "{}")
        _write("reports/api_failure.json", "{}")
        _write("reports/notes.txt")
        assert collect_files(["reports/*.json"], runner_dir, NOW) == []
        assert _collected(runner_dir) == ["reports/api_failure.json", "reports/api_success.json"]
        assert Path("reports/api_success.json").is_file()

    def test_a_folder_stands_for_every_file_below_it(self, runner_dir):
        _write("shots/a.png")
        _write("shots/deep/b.png")
        assert collect_files(["shots"], runner_dir, NOW) == []
        assert _collected(runner_dir) == ["shots/a.png", "shots/deep/b.png"]

    def test_a_file_older_than_the_runner_is_left_alone(self, runner_dir):
        _write("reports/old_failure.json", age=3600)
        _write("reports/new_success.json")
        assert collect_files(["reports/*.json"], runner_dir, NOW) == []
        assert _collected(runner_dir) == ["reports/new_success.json"]

    def test_only_stale_matches_is_a_warning(self, runner_dir):
        _write("reports/old_failure.json", age=3600)
        assert collect_files(["reports/*.json"], runner_dir, NOW) == [
            "artifact pattern 'reports/*.json' matched no file written by this runner"]
        assert not (runner_dir / "collected").exists()

    def test_no_match_is_a_warning(self, runner_dir):
        assert collect_files(["absent/*.json"], runner_dir, NOW) == [
            "artifact pattern 'absent/*.json' matched no file written by this runner"]

    def test_a_pattern_the_runner_satisfied_in_its_own_directory_is_not_a_warning(self, runner_dir):
        # A runner that reads TEST_PIONEER_ARTIFACT_DIR writes "reports/api_x" below that directory.
        (runner_dir / "reports").mkdir()
        (runner_dir / "reports" / "api_x_success.json").write_text("{}", encoding="utf-8")
        assert collect_files(["reports/api_*.json"], runner_dir, NOW) == []
        assert not (runner_dir / "collected").exists()

    def test_a_refused_pattern_is_a_warning_and_copies_nothing(self, runner_dir, tmp_path):
        outside = tmp_path.parent / "outside_collect.json"
        outside.write_text("{}", encoding="utf-8")
        try:
            assert collect_files(["../outside_collect.json"], runner_dir, NOW) == [
                "artifact pattern '../outside_collect.json' is not used: it leaves the working directory"]
        finally:
            outside.unlink()
        assert not (runner_dir / "collected").exists()

    def test_the_run_directory_itself_is_never_collected(self, runner_dir):
        (runner_dir / "stdout.log").write_text("captured", encoding="utf-8")
        _write("result.log")
        assert collect_files(["**/*.log"], runner_dir, NOW) == []
        assert _collected(runner_dir) == ["result.log"]

    def test_each_pattern_is_judged_on_its_own(self, runner_dir):
        _write("a.json")
        warnings = collect_files(["a.json", "b.json", "/c.json"], runner_dir, NOW)
        assert _collected(runner_dir) == ["a.json"]
        assert warnings == [
            "artifact pattern 'b.json' matched no file written by this runner",
            "artifact pattern '/c.json' is not used: it is not relative to the working directory",
        ]

    def test_a_copy_that_fails_is_a_warning(self, runner_dir):
        _write("a.json")
        (runner_dir / "collected").write_text("a file where the folder should go", encoding="utf-8")
        (warning,) = collect_files(["a.json"], runner_dir, NOW)
        assert warning.startswith("artifact pattern 'a.json' could not be collected:")
