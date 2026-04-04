"""Tests for test_pioneer.executor.time.wait"""
from unittest.mock import patch

from test_pioneer.executor.time.wait import blocked_wait


class TestBlockedWait:
    @patch("test_pioneer.executor.time.wait.time.sleep")
    def test_valid_wait(self, mock_sleep):
        result = blocked_wait({"wait": 3})
        assert result is True
        mock_sleep.assert_called_once_with(3)

    def test_non_int_returns_false(self):
        result = blocked_wait({"wait": "not_int"})
        assert result is False

    def test_missing_wait_returns_false(self):
        result = blocked_wait({})
        assert result is False

    @patch("test_pioneer.executor.time.wait.time.sleep")
    def test_zero_wait(self, mock_sleep):
        result = blocked_wait({"wait": 0})
        assert result is True
        mock_sleep.assert_called_once_with(0)
