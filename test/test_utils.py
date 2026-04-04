"""Tests for test_pioneer.utils modules"""
from test_pioneer.utils.package.check import is_installed
from test_pioneer.utils.exception.exceptions import (
    ExecutorException, YamlException, WrongInputException, ProjectException,
)


class TestIsInstalled:
    def test_installed_package(self):
        assert is_installed("os") is True

    def test_not_installed_package(self):
        assert is_installed("nonexistent_package_xyz_12345") is False

    def test_stdlib_package(self):
        assert is_installed("json") is True


class TestExceptions:
    def test_executor_exception(self):
        exc = ExecutorException("test")
        assert str(exc) == "test"
        assert isinstance(exc, Exception)

    def test_yaml_exception(self):
        exc = YamlException("test")
        assert str(exc) == "test"
        assert isinstance(exc, Exception)

    def test_wrong_input_exception(self):
        exc = WrongInputException("test")
        assert str(exc) == "test"
        assert isinstance(exc, Exception)

    def test_project_exception(self):
        exc = ProjectException("test")
        assert str(exc) == "test"
        assert isinstance(exc, Exception)
