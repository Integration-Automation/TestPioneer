"""``run_folder`` hands the runner every JSON file in the folder, as sorted string paths."""
from unittest.mock import MagicMock, patch

from test_pioneer.executor.run.executor_run_folder import run_folder


def test_run_folder_passes_sorted_string_paths(tmp_path, monkeypatch):
    folder = tmp_path / "actions"
    folder.mkdir()
    for name in ("b.json", "a.json", "notes.txt"):
        (folder / name).write_text("[]", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    runner = MagicMock()
    with patch("test_pioneer.executor.run.executor_run_folder.select_with_runner",
               return_value=(True, runner)):
        assert run_folder({"with": "api-runner", "run_folder": "actions"}) is True  # nosec B101
    runner.assert_called_once_with([str(folder / "a.json"), str(folder / "b.json")])


def test_run_folder_with_a_real_runner_executes_every_file(tmp_path, monkeypatch, capsys):
    """End to end with LoadDensity's executor: both files' actions run (a print each)."""
    monkeypatch.setenv("LOCUST_SKIP_MONKEY_PATCH", "1")
    folder = tmp_path / "actions"
    folder.mkdir()
    (folder / "one.json").write_text('[["print", ["run-folder-one"]]]', encoding="utf-8")
    (folder / "two.json").write_text('[["print", ["run-folder-two"]]]', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    assert run_folder({"with": "load-runner", "run_folder": "actions"}) is True  # nosec B101
    printed = capsys.readouterr().out.splitlines()
    assert "run-folder-one" in printed  # nosec B101
    assert "run-folder-two" in printed  # nosec B101
