"""Tests for test_pioneer.executor.run.parallel_run"""
from unittest.mock import patch, MagicMock

from test_pioneer.executor.run.parallel_run import parallel_run


class TestParallelRun:
    def test_missing_parallel_run_tag(self):
        result = parallel_run({"parallel_run": None})
        assert result is False

    def test_mismatched_runners_and_scripts(self):
        step = {
            "parallel_run": {
                "runners": ["api-runner", "web-runner"],
                "scripts": ["test1.json"],
            }
        }
        result = parallel_run(step)
        assert result is False

    @patch("test_pioneer.executor.run.parallel_run.is_installed", return_value=False)
    def test_gui_runner_not_installed(self, mock_installed):
        step = {
            "parallel_run": {
                "runners": ["gui-runner"],
                "scripts": ["test.json"],
            }
        }
        result = parallel_run(step)
        assert result is False

    @patch("test_pioneer.executor.run.parallel_run.subprocess.Popen")
    @patch("test_pioneer.executor.run.parallel_run.is_installed", return_value=False)
    def test_script_not_found_skips(self, mock_installed, mock_popen, tmp_path):
        step = {
            "parallel_run": {
                "runners": ["api-runner"],
                "scripts": [str(tmp_path / "nonexistent.json")],
            }
        }
        result = parallel_run(step)
        assert result is True
        mock_popen.assert_not_called()

    @patch("test_pioneer.executor.run.parallel_run.subprocess.Popen")
    @patch("test_pioneer.executor.run.parallel_run.is_installed", return_value=False)
    def test_valid_parallel_run(self, mock_installed, mock_popen, tmp_path):
        script = tmp_path / "test.json"
        script.write_text("{}", encoding="utf-8")

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        mock_proc.returncode = None
        # Simulate process completing on second poll
        def side_effect():
            mock_proc.returncode = 0
            return 0
        mock_proc.poll.side_effect = [None, side_effect()]
        mock_popen.return_value = mock_proc

        step = {
            "parallel_run": {
                "runners": ["api-runner"],
                "scripts": [str(script)],
            }
        }
        result = parallel_run(step)
        assert result is True

    def test_unknown_runner_skips(self, tmp_path):
        script = tmp_path / "test.json"
        script.write_text("{}", encoding="utf-8")

        step = {
            "parallel_run": {
                "runners": ["unknown-runner"],
                "scripts": [str(script)],
            }
        }
        result = parallel_run(step)
        assert result is True  # Returns True after skipping unknown runner
