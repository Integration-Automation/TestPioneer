"""Tests for test_pioneer.executor.browser.url"""
from unittest.mock import patch

from test_pioneer.executor.browser.url import open_url


class TestOpenUrl:
    def test_valid_url_default_method(self):
        with patch("test_pioneer.executor.browser.url.webbrowser") as mock_wb:
            result = open_url({"open_url": "https://example.com"})
            assert result is True
            mock_wb.open.assert_called_once_with(url="https://example.com")

    def test_valid_url_open_new_tab(self):
        with patch("test_pioneer.executor.browser.url.webbrowser") as mock_wb:
            step = {"open_url": "https://example.com", "url_open_method": "open_new_tab"}
            result = open_url(step)
            assert result is True
            mock_wb.open_new_tab.assert_called_once_with(url="https://example.com")

    def test_valid_url_open_new(self):
        with patch("test_pioneer.executor.browser.url.webbrowser") as mock_wb:
            step = {"open_url": "https://example.com", "url_open_method": "open_new"}
            result = open_url(step)
            assert result is True
            mock_wb.open_new.assert_called_once_with(url="https://example.com")

    def test_non_string_url_returns_false(self):
        result = open_url({"open_url": 123})
        assert result is False

    def test_missing_url_returns_false(self):
        result = open_url({})
        assert result is False

    def test_invalid_method_returns_false(self):
        with patch("test_pioneer.executor.browser.url.webbrowser"):
            step = {"open_url": "https://example.com", "url_open_method": "invalid"}
            result = open_url(step)
            assert result is False

    def test_exception_returns_false(self):
        with patch("test_pioneer.executor.browser.url.webbrowser") as mock_wb:
            mock_wb.open.side_effect = Exception("browser error")
            result = open_url({"open_url": "https://example.com"})
            assert result is False
