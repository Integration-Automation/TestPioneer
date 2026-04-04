"""Tests for test_pioneer.executor.run.utils"""
from unittest.mock import patch, MagicMock

from test_pioneer.executor.run.utils import select_with_runner


# Common mock modules for runner imports
_MOCK_RUNNER_MODULES = {
    "je_web_runner": MagicMock(execute_action=MagicMock()),
    "je_api_testka": MagicMock(execute_action=MagicMock()),
    "je_load_density": MagicMock(execute_action=MagicMock()),
}


class TestSelectWithRunner:
    def test_missing_with_tag(self):
        result = select_with_runner({"run": "test.json"}, enable_logging=False)
        assert result == (False, None)

    def test_non_string_with_tag(self):
        result = select_with_runner({"with": 123}, enable_logging=False)
        assert result == (False, None)

    @patch.dict("sys.modules", _MOCK_RUNNER_MODULES)
    @patch("test_pioneer.executor.run.utils.is_installed", return_value=False)
    def test_gui_runner_not_installed(self, mock_installed):
        step = {"with": "gui-runner", "run": "test.json"}
        ok, runner = select_with_runner(step, enable_logging=False, mode="run")
        assert ok is False
        assert runner is None

    @patch.dict("sys.modules", _MOCK_RUNNER_MODULES)
    @patch("test_pioneer.executor.run.utils.is_installed", return_value=False)
    def test_invalid_runner_tag(self, mock_installed):
        step = {"with": "invalid-runner", "run": "test.json"}
        ok, runner = select_with_runner(step, enable_logging=False, mode="run")
        assert ok is False
        assert runner is None

    @patch.dict("sys.modules", _MOCK_RUNNER_MODULES)
    @patch("test_pioneer.executor.run.utils.is_installed", return_value=False)
    def test_api_runner_selection(self, mock_installed):
        step = {"with": "api-runner", "run": "test.json"}
        ok, runner = select_with_runner(step, enable_logging=False, mode="run")
        assert ok is True
        assert runner is not None

    @patch.dict("sys.modules", _MOCK_RUNNER_MODULES)
    @patch("test_pioneer.executor.run.utils.is_installed", return_value=False)
    def test_web_runner_selection(self, mock_installed):
        step = {"with": "web-runner", "run": "test.json"}
        ok, runner = select_with_runner(step, enable_logging=False, mode="run")
        assert ok is True
        assert runner is not None

    @patch.dict("sys.modules", _MOCK_RUNNER_MODULES)
    @patch("test_pioneer.executor.run.utils.is_installed", return_value=False)
    def test_load_runner_selection(self, mock_installed):
        step = {"with": "load-runner", "run": "test.json"}
        ok, runner = select_with_runner(step, enable_logging=False, mode="run")
        assert ok is True
        assert runner is not None

    @patch.dict("sys.modules", _MOCK_RUNNER_MODULES)
    @patch("test_pioneer.executor.run.utils.is_installed", return_value=False)
    def test_invalid_mode_returns_false(self, mock_installed):
        step = {"with": "api-runner", "run": "test.json"}
        ok, runner = select_with_runner(step, enable_logging=False, mode="invalid")
        assert ok is False
        assert runner is None

    @patch.dict("sys.modules", _MOCK_RUNNER_MODULES)
    @patch("test_pioneer.executor.run.utils.is_installed", return_value=False)
    def test_gui_runner_not_installed_run_folder_mode(self, mock_installed):
        step = {"with": "gui-runner", "run_folder": "./test"}
        ok, runner = select_with_runner(step, enable_logging=False, mode="run_folder")
        assert ok is False
        assert runner is None
