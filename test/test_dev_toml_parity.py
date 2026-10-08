"""``dev.toml`` describes the same package as ``pyproject.toml`` under another name.

The dev channel (``test_pioneer_dev``) is built by writing ``dev.toml`` to ``pyproject.toml``, while
the tests run against an install of ``pyproject.toml``. A dependency, an extra or a packaging rule
on one side only ships a dev package that differs from what was tested.
"""
from __future__ import annotations

from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")  # reason: stdlib from 3.11; CI also runs 3.10

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str) -> dict:
    """Return the parsed TOML file ``name`` from the repository root."""
    with (REPO_ROOT / name).open("rb") as handle:
        return tomllib.load(handle)


STABLE_FILE = _load("pyproject.toml")
DEV_FILE = _load("dev.toml")
STABLE = STABLE_FILE["project"]
DEV = DEV_FILE["project"]


def test_package_names_differ():
    """The two files publish under different names."""
    assert STABLE["name"] == "test_pioneer"
    assert DEV["name"] == "test_pioneer_dev"


def test_runtime_dependencies_match():
    """Both packages declare the same runtime dependencies."""
    assert sorted(DEV["dependencies"]) == sorted(STABLE["dependencies"])


def test_python_floor_matches():
    """Both packages need the same minimum Python."""
    assert DEV["requires-python"] == STABLE["requires-python"]


def test_optional_dependency_groups_match():
    """Both packages offer the same extras."""
    assert DEV.get("optional-dependencies", {}) == STABLE.get("optional-dependencies", {})


@pytest.mark.parametrize("table", ["scripts", "gui-scripts", "entry-points"])
def test_entry_points_match(table):
    """Both packages declare the same console scripts, GUI scripts and entry points."""
    assert DEV.get(table, {}) == STABLE.get(table, {})


def test_shipped_files_match():
    """Package discovery and package data, which decide what reaches the wheel, are the same."""
    assert DEV_FILE["tool"]["setuptools"] == STABLE_FILE["tool"]["setuptools"]
