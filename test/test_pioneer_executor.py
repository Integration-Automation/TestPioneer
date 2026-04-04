"""Tests for test_pioneer.executor.pioneer_executor"""
import pytest
from unittest.mock import patch, MagicMock

from test_pioneer.executor.pioneer_executor import execute_yaml, _load_yaml, _validate_steps
from test_pioneer.utils.exception.exceptions import WrongInputException, YamlException


class TestLoadYaml:
    def test_load_from_string(self):
        yaml_str = "jobs:\n  steps:\n    - name: test"
        result = _load_yaml(yaml_str, "String")
        assert isinstance(result, dict)
        assert "jobs" in result

    def test_load_from_file(self, tmp_path):
        yaml_file = tmp_path / "test.yml"
        yaml_file.write_text("jobs:\n  steps:\n    - name: test", encoding="utf-8")
        result = _load_yaml(str(yaml_file), "File")
        assert isinstance(result, dict)

    def test_load_invalid_type_raises(self):
        with pytest.raises(WrongInputException):
            _load_yaml("some_data", "InvalidType")

    def test_load_non_dict_raises(self):
        with pytest.raises(YamlException, match="Not a dict"):
            _load_yaml("- item1\n- item2", "String")


class TestValidateSteps:
    def test_valid_steps(self):
        steps = [{"name": "step1"}, {"name": "step2"}]
        assert _validate_steps(steps, enable_logging=False) is True

    def test_missing_name(self):
        steps = [{"run": "test.json"}]
        assert _validate_steps(steps, enable_logging=False) is False

    def test_duplicate_name(self):
        steps = [{"name": "dup"}, {"name": "dup"}]
        assert _validate_steps(steps, enable_logging=False) is False


class TestExecuteYaml:
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_no_jobs_tag_raises(self, mock_installed, mock_logger):
        with pytest.raises(YamlException, match="No jobs tag"):
            execute_yaml("key: value", yaml_type="String")

    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_jobs_not_dict_raises(self, mock_installed, mock_logger):
        with pytest.raises(YamlException, match="jobs not a dict"):
            execute_yaml("jobs: not_a_dict", yaml_type="String")

    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_empty_steps_raises(self, mock_installed, mock_logger):
        with pytest.raises(YamlException, match="Steps tag is empty"):
            execute_yaml("jobs:\n  steps:", yaml_type="String")

    @patch("test_pioneer.executor.pioneer_executor.blocked_wait", return_value=True)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_wait_step(self, mock_installed, mock_logger, mock_wait):
        yaml_str = "jobs:\n  steps:\n    - name: wait_test\n      wait: 5"
        execute_yaml(yaml_str, yaml_type="String")
        mock_wait.assert_called_once()
        step_arg = mock_wait.call_args[1]["step"]
        assert step_arg["wait"] == 5

    @patch("test_pioneer.executor.pioneer_executor.open_url", return_value=True)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_open_url_step(self, mock_installed, mock_logger, mock_open_url):
        yaml_str = "jobs:\n  steps:\n    - name: url_test\n      open_url: https://example.com"
        execute_yaml(yaml_str, yaml_type="String")
        mock_open_url.assert_called_once()

    @patch("test_pioneer.executor.pioneer_executor.run", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_step_failure_stops_execution(self, mock_installed, mock_logger, mock_run):
        yaml_str = (
            "jobs:\n  steps:\n"
            "    - name: step1\n      run: test.json\n      with: api-runner\n"
            "    - name: step2\n      run: test2.json\n      with: api-runner"
        )
        execute_yaml(yaml_str, yaml_type="String")
        # Only the first step should be called since it returned False
        assert mock_run.call_count == 1

    @patch("test_pioneer.executor.pioneer_executor.download_single_file", return_value=True)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_download_file_step(self, mock_installed, mock_logger, mock_download):
        yaml_str = (
            "jobs:\n  steps:\n"
            "    - name: dl_test\n      download_file: http://example.com/f.zip\n      file_path: f.zip"
        )
        execute_yaml(yaml_str, yaml_type="String")
        mock_download.assert_called_once()

    @patch("test_pioneer.executor.pioneer_executor.open_program", return_value=True)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_open_program_step(self, mock_installed, mock_logger, mock_open):
        yaml_str = "jobs:\n  steps:\n    - name: prog_test\n      open_program: notepad.exe"
        execute_yaml(yaml_str, yaml_type="String")
        mock_open.assert_called_once()
        assert mock_open.call_args[1]["name"] == "prog_test"

    @patch("test_pioneer.executor.pioneer_executor.close_program", return_value=True)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_close_program_step(self, mock_installed, mock_logger, mock_close):
        yaml_str = "jobs:\n  steps:\n    - name: close_test\n      close_program: notepad.exe"
        execute_yaml(yaml_str, yaml_type="String")
        mock_close.assert_called_once()

    @patch("test_pioneer.executor.pioneer_executor.unzip_zipfile", return_value=True)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_unzip_step(self, mock_installed, mock_logger, mock_unzip):
        yaml_str = "jobs:\n  steps:\n    - name: zip_test\n      unzip_zipfile: test.zip"
        execute_yaml(yaml_str, yaml_type="String")
        mock_unzip.assert_called_once()

    @patch("test_pioneer.executor.pioneer_executor.parallel_run", return_value=True)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_parallel_run_step(self, mock_installed, mock_logger, mock_parallel):
        yaml_str = (
            "jobs:\n  steps:\n    - name: par_test\n"
            "      parallel_run:\n        runners: [api-runner]\n        scripts: [test.json]"
        )
        execute_yaml(yaml_str, yaml_type="String")
        mock_parallel.assert_called_once()

    @patch("test_pioneer.executor.pioneer_executor.run_folder", return_value=True)
    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_run_folder_step(self, mock_installed, mock_logger, mock_run_folder):
        yaml_str = "jobs:\n  steps:\n    - name: folder_test\n      run_folder: ./test\n      with: api-runner"
        execute_yaml(yaml_str, yaml_type="String")
        mock_run_folder.assert_called_once()

    @patch("test_pioneer.executor.pioneer_executor.set_logger", return_value=False)
    @patch("test_pioneer.executor.pioneer_executor.is_installed", return_value=False)
    def test_duplicate_step_names_returns_early(self, mock_installed, mock_logger):
        yaml_str = (
            "jobs:\n  steps:\n"
            "    - name: dup\n      wait: 1\n"
            "    - name: dup\n      wait: 2"
        )
        # Should return without error (just returns None early)
        execute_yaml(yaml_str, yaml_type="String")
