"""Tests for test_pioneer.executor.file.file_processing"""
import sys
from unittest.mock import patch, MagicMock

# Mock automation_file before importing the module under test
mock_automation_file = MagicMock()
sys.modules["automation_file"] = mock_automation_file

from test_pioneer.executor.file.file_processing import download_single_file, unzip_zipfile


class TestDownloadSingleFile:
    def setup_method(self):
        mock_automation_file.reset_mock()

    def test_valid_download(self):
        step = {"download_file": "http://example.com/f.zip", "file_path": "f.zip"}
        result = download_single_file(step)
        assert result is True
        mock_automation_file.download_file.assert_called_once_with(
            file_url="http://example.com/f.zip", file_name="f.zip"
        )

    def test_missing_url_returns_false(self):
        result = download_single_file({"file_path": "f.zip"})
        assert result is False

    def test_missing_file_path_returns_false(self):
        result = download_single_file({"download_file": "http://example.com/f.zip"})
        assert result is False

    def test_non_string_url_returns_false(self):
        result = download_single_file({"download_file": 123, "file_path": "f.zip"})
        assert result is False

    def test_non_string_path_returns_false(self):
        result = download_single_file({"download_file": "http://example.com/f.zip", "file_path": 123})
        assert result is False


class TestUnzipZipfile:
    def setup_method(self):
        mock_automation_file.reset_mock()

    def test_valid_unzip(self):
        step = {"zip_file_path": "test.zip"}
        result = unzip_zipfile(step)
        assert result is True
        mock_automation_file.unzip_all.assert_called_once_with(zip_file_path="test.zip")

    def test_unzip_with_password_and_extract_path(self):
        step = {"zip_file_path": "test.zip", "password": "secret", "extract_path": "/tmp"}
        result = unzip_zipfile(step)
        assert result is True
        mock_automation_file.unzip_all.assert_called_once_with(
            zip_file_path="test.zip", password="secret", extract_path="/tmp"
        )

    def test_missing_zip_path_returns_false(self):
        result = unzip_zipfile({})
        assert result is False

    def test_non_string_zip_path_returns_false(self):
        result = unzip_zipfile({"zip_file_path": 123})
        assert result is False
