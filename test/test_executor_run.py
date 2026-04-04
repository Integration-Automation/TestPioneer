"""Tests for test_pioneer.executor.run.executor_run and executor_run_folder"""
import json
from unittest.mock import patch, MagicMock

from test_pioneer.executor.run.executor_run import run
from test_pioneer.executor.run.executor_run_folder import run_folder


class TestRun:
    @patch("test_pioneer.executor.run.executor_run.select_with_runner")
    def test_runner_selection_failure(self, mock_select):
        mock_select.return_value = (False, None)
        result = run({"run": "test.json", "with": "api-runner"})
        assert result is False

    @patch("test_pioneer.executor.run.executor_run.select_with_runner")
    def test_non_string_path_returns_false(self, mock_select):
        mock_select.return_value = (True, MagicMock())
        result = run({"run": 123, "with": "api-runner"})
        assert result is False

    @patch("test_pioneer.executor.run.executor_run.select_with_runner")
    def test_file_not_exist_returns_false(self, mock_select):
        mock_select.return_value = (True, MagicMock())
        result = run({"run": "nonexistent_file.json", "with": "api-runner"})
        assert result is False

    @patch("test_pioneer.executor.run.executor_run.select_with_runner")
    def test_valid_json_file(self, mock_select, tmp_path):
        mock_runner = MagicMock()
        mock_select.return_value = (True, mock_runner)

        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps({"action": "test"}), encoding="utf-8")

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = run({"run": "test.json", "with": "api-runner"})
        assert result is True
        mock_runner.assert_called_once_with({"action": "test"})

    @patch("test_pioneer.executor.run.executor_run.select_with_runner")
    def test_invalid_json_returns_false(self, mock_select, tmp_path):
        mock_select.return_value = (True, MagicMock())

        json_file = tmp_path / "bad.json"
        json_file.write_text("not json content", encoding="utf-8")

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = run({"run": "bad.json", "with": "api-runner"})
        assert result is False


class TestRunFolder:
    @patch("test_pioneer.executor.run.executor_run_folder.select_with_runner")
    def test_runner_selection_failure(self, mock_select):
        mock_select.return_value = (False, None)
        result = run_folder({"run_folder": "./test", "with": "api-runner"})
        assert result is False

    @patch("test_pioneer.executor.run.executor_run_folder.select_with_runner")
    def test_non_string_path_returns_false(self, mock_select):
        mock_select.return_value = (True, MagicMock())
        result = run_folder({"run_folder": 123, "with": "api-runner"})
        assert result is False

    @patch("test_pioneer.executor.run.executor_run_folder.select_with_runner")
    def test_folder_not_exist_returns_false(self, mock_select):
        mock_select.return_value = (True, MagicMock())
        result = run_folder({"run_folder": "nonexistent_folder", "with": "api-runner"})
        assert result is False

    @patch("test_pioneer.executor.run.executor_run_folder.select_with_runner")
    def test_empty_folder_returns_false(self, mock_select, tmp_path):
        mock_select.return_value = (True, MagicMock())
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = run_folder({"run_folder": "empty", "with": "api-runner"})
        assert result is False

    @patch("test_pioneer.executor.run.executor_run_folder.select_with_runner")
    def test_folder_with_json_files(self, mock_select, tmp_path):
        mock_runner = MagicMock()
        mock_select.return_value = (True, mock_runner)

        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test1.json").write_text("{}", encoding="utf-8")
        (test_dir / "test2.json").write_text("{}", encoding="utf-8")

        with patch("os.getcwd", return_value=str(tmp_path)):
            result = run_folder({"run_folder": "tests", "with": "gui-runner"})
        assert result is True
        mock_runner.assert_called_once()
        # Verify JSON files were passed
        json_files = mock_runner.call_args[0][0]
        assert len(json_files) == 2
