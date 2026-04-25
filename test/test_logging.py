"""Tests for test_pioneer.logging.loggin_instance and test_recorder.logger"""
import logging
from unittest.mock import MagicMock

from test_pioneer.logging.loggin_instance import step_log_check, test_pioneer_logger, TestPioneerHandler
from test_pioneer.executor.test_recorder.logger import set_logger


class TestStepLogCheck:
    def test_logs_info_when_enabled(self):
        mock_logger = MagicMock(spec=logging.Logger)
        step_log_check(enable_logging=True, logger=mock_logger, level="info", message="test msg")
        mock_logger.info.assert_called_once_with("test msg")

    def test_logs_error_when_enabled(self):
        mock_logger = MagicMock(spec=logging.Logger)
        step_log_check(enable_logging=True, logger=mock_logger, level="error", message="error msg")
        mock_logger.error.assert_called_once_with("error msg")

    def test_no_log_when_disabled(self):
        mock_logger = MagicMock(spec=logging.Logger)
        step_log_check(enable_logging=False, logger=mock_logger, level="info", message="test msg")
        mock_logger.info.assert_not_called()

    def test_no_log_when_no_message(self):
        mock_logger = MagicMock(spec=logging.Logger)
        step_log_check(enable_logging=True, logger=mock_logger, level="info", message=None)
        mock_logger.info.assert_not_called()

    def test_invalid_level_does_nothing(self):
        mock_logger = MagicMock(spec=logging.Logger)
        step_log_check(enable_logging=True, logger=mock_logger, level="warning", message="msg")
        mock_logger.info.assert_not_called()
        mock_logger.error.assert_not_called()


class TestTestPioneerHandler:
    def test_handler_creation(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        handler = TestPioneerHandler(filename=log_file)
        try:
            assert handler.maxBytes > 0
            assert handler.backupCount == 0
        finally:
            handler.close()

    def test_handler_emit(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        handler = TestPioneerHandler(filename=log_file)
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="test message", args=None, exc_info=None
        )
        handler.emit(record)
        handler.close()
        with open(log_file, "r") as f:
            content = f.read()
        assert "test message" in content


class TestSetLogger:
    def test_set_logger_with_pioneer_log(self, tmp_path):
        log_file = str(tmp_path / "test.log")
        result = set_logger({"pioneer_log": log_file})
        assert result is True
        # Clean up handler
        for handler in test_pioneer_logger.handlers[:]:
            if isinstance(handler, TestPioneerHandler):
                handler.close()
                test_pioneer_logger.removeHandler(handler)

    def test_set_logger_without_pioneer_log(self):
        result = set_logger({})
        assert result is False

    def test_set_logger_with_none_value(self):
        result = set_logger({"pioneer_log": None})
        assert result is False
