"""Tests for test_pioneer.executor.run.process_manager"""
from unittest.mock import MagicMock

from test_pioneer.executor.run.process_manager import ProcessManager, process_manager


class TestProcessManagerRun:
    def test_add_process(self):
        pm = ProcessManager()
        mock_proc = MagicMock()
        pm.add_process(mock_proc)
        assert mock_proc in pm.process_list

    def test_remove_process(self):
        pm = ProcessManager()
        mock_proc = MagicMock()
        pm.add_process(mock_proc)
        pm.remove_process(mock_proc)
        assert mock_proc not in pm.process_list

    def test_remove_nonexistent_process(self):
        pm = ProcessManager()
        mock_proc = MagicMock()
        pm.remove_process(mock_proc)  # Should not raise

    def test_cleanup_finished(self):
        pm = ProcessManager()
        finished = MagicMock()
        finished.returncode = 0
        running = MagicMock()
        running.returncode = None

        pm.process_list = [finished, running]
        pm.cleanup_finished()
        assert finished not in pm.process_list
        assert running in pm.process_list

    def test_terminate_all(self):
        pm = ProcessManager()
        proc1 = MagicMock()
        proc2 = MagicMock()
        pm.process_list = [proc1, proc2]

        pm.terminate_all()
        proc1.terminate.assert_called_once()
        proc2.terminate.assert_called_once()
        assert len(pm.process_list) == 0

    def test_global_instance_exists(self):
        assert process_manager is not None
        assert isinstance(process_manager, ProcessManager)
