"""Tests for test_pioneer.process modules"""
from unittest.mock import patch, MagicMock

from test_pioneer.process.execute_process import ExecuteProcess
from test_pioneer.process.process_manager import ProcessManager


class TestExecuteProcess:
    def test_init_defaults(self):
        ep = ExecuteProcess()
        assert ep.process is None
        import subprocess
        assert ep.redirect_stdout == subprocess.PIPE
        assert ep.redirect_stderr == subprocess.PIPE

    @patch("test_pioneer.process.execute_process.subprocess.Popen")
    def test_start_process_pipe(self, mock_popen):
        ep = ExecuteProcess()
        ep.start_process("echo hello")
        mock_popen.assert_called_once()
        assert ep.process is not None

    @patch("test_pioneer.process.execute_process.subprocess.Popen")
    def test_start_process_with_file_redirect(self, mock_popen, tmp_path):
        stdout_path = str(tmp_path / "out.log")
        stderr_path = str(tmp_path / "err.log")
        ep = ExecuteProcess(redirect_stdout=stdout_path, redirect_stderr=stderr_path)
        ep.start_process("echo hello")
        mock_popen.assert_called_once()
        # Verify file handles were opened
        assert ep._stdout_file is not None
        assert ep._stderr_file is not None
        ep._stdout_file.close()
        ep._stderr_file.close()

    def test_exit_program_no_process(self):
        ep = ExecuteProcess()
        ep.exit_program()  # Should not raise

    @patch("test_pioneer.process.execute_process.psutil.Process")
    def test_exit_program_kills_tree(self, mock_psutil):
        ep = ExecuteProcess()
        ep.process = MagicMock()
        ep.process.pid = 12345

        mock_child = MagicMock()
        mock_psutil.return_value.children.return_value = [mock_child]

        ep.exit_program()
        mock_child.kill.assert_called_once()
        mock_psutil.return_value.kill.assert_called_once()


class TestProcessManager:
    def test_close_process_existing(self):
        pm = ProcessManager()
        mock_ep = MagicMock()
        pm.process_dict["test"] = mock_ep
        pm.name_set.add("test")

        pm.close_process("test")
        mock_ep.exit_program.assert_called_once()
        assert "test" not in pm.process_dict
        assert "test" not in pm.name_set

    def test_close_process_nonexistent(self):
        pm = ProcessManager()
        pm.close_process("nonexistent")  # Should not raise
