"""The source distribution carries no tests.

setuptools adds ``test/test*.py`` to an sdist by default, so ``MANIFEST.in`` prunes the test
directory. ``prune`` matches whole directory names: ``test/`` goes and the package,
``test_pioneer/``, stays. Both packages (``pyproject.toml`` and ``dev.toml``) are built with this
one ``MANIFEST.in``. It is read as text here; nothing is built.
"""
from __future__ import annotations

from fnmatch import fnmatchcase
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_DIRECTORY = Path(__file__).resolve().parent.name
PACKAGE = "test_pioneer"
_REMOVING = {"prune", "exclude", "recursive-exclude", "global-exclude"}


def _commands() -> list[list[str]]:
    """Return each ``MANIFEST.in`` command as its words, without comments and blank lines."""
    lines = (REPO_ROOT / "MANIFEST.in").read_text(encoding="utf-8").splitlines()
    return [line.split() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def test_sdist_removes_the_test_directory_and_nothing_else() -> None:
    """The only thing ``MANIFEST.in`` takes out is the test directory, named literally."""
    removing = [command for command in _commands() if command[0] in _REMOVING]
    assert removing == [["prune", TEST_DIRECTORY]]


def test_prune_does_not_match_the_package() -> None:
    """No pruned pattern also matches the package, as ``prune test*`` would."""
    assert (REPO_ROOT / PACKAGE / "__init__.py").is_file()
    pruned = [pattern for command in _commands() if command[0] == "prune" for pattern in command[1:]]
    assert TEST_DIRECTORY in pruned
    assert [pattern for pattern in pruned if fnmatchcase(PACKAGE, pattern)] == []


def test_nothing_puts_the_tests_back() -> None:
    """Pruning the test directory is the last command, so no later one restores a test file."""
    assert _commands()[-1] == ["prune", TEST_DIRECTORY]
