"""Tests for test_pioneer.executor.program.external_program"""
from unittest.mock import patch, MagicMock

from test_pioneer.executor.program.external_program import open_program, close_program
from test_pioneer.process.process_manager import process_manager_instance


class TestOpenProgram:
    @patch("test_pioneer.executor.program.external_program.ExecuteProcess")
    def test_open_program_basic(self, mock_ep_class):
        mock_ep = MagicMock()
        mock_ep_class.return_value = mock_ep

        step = {"open_program": "notepad.exe"}
        result = open_program(step, name="test_notepad")
        assert result is True
        mock_ep.start_process.assert_called_once_with("notepad.exe")
        assert "test_notepad" in process_manager_instance.process_dict

    @patch("test_pioneer.executor.program.external_program.ExecuteProcess")
    def test_open_program_with_redirects(self, mock_ep_class):
        mock_ep = MagicMock()
        mock_ep_class.return_value = mock_ep

        step = {
            "open_program": "notepad.exe",
            "redirect_stdout": "stdout.log",
            "redirect_stderr": "stderr.log",
        }
        result = open_program(step, name="test_notepad2")
        assert result is True
        assert mock_ep.redirect_stdout == "stdout.log"
        assert mock_ep.redirect_stderr == "stderr.log"

    def test_non_string_program_returns_false(self):
        result = open_program({"open_program": 123}, name="test")
        assert result is False

    def test_non_string_stdout_returns_false(self):
        step = {"open_program": "notepad.exe", "redirect_stdout": 123}
        result = open_program(step, name="test")
        assert result is False

    def test_non_string_stderr_returns_false(self):
        step = {"open_program": "notepad.exe", "redirect_stderr": 123}
        result = open_program(step, name="test")
        assert result is False


class TestCloseProgram:
    def test_close_program_valid(self):
        mock_ep = MagicMock()
        process_manager_instance.process_dict["my_prog"] = mock_ep
        process_manager_instance.name_set.add("my_prog")

        result = close_program({"close_program": "my_prog"})
        assert result is True
        mock_ep.exit_program.assert_called_once()

    def test_close_program_not_found(self):
        result = close_program({"close_program": "nonexistent"})
        assert result is True  # close_program always returns True

    def test_non_string_returns_false(self):
        result = close_program({"close_program": 123})
        assert result is False
