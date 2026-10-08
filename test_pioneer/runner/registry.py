"""The runners a workflow can name, and the package behind each one.

The JSON Schema, the linter and ``parallel_run`` all read this table, so a runner is declared once.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

GUI_RUNNER = "gui-runner"

RUNNER_PACKAGES: Mapping[str, str] = MappingProxyType({
    GUI_RUNNER: "je_auto_control",
    "web-runner": "je_web_runner",
    "api-runner": "je_api_testka",
    "load-runner": "je_load_density",
    "file-runner": "automation_file",
})
RUNNER_NAMES: tuple[str, ...] = tuple(RUNNER_PACKAGES)

# Runners whose package comes from an extra (``test_pioneer[gui]``) instead of a core dependency.
OPTIONAL_RUNNERS: frozenset[str] = frozenset({GUI_RUNNER})
