"""The runners a workflow can name, and the adapter behind each one.

The JSON Schema, the linter and ``parallel_run`` all read this table, so a runner is declared once.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from test_pioneer.runner.adapter import ModuleRunner, RunnerAdapter

GUI_RUNNER = "gui-runner"

RUNNERS: Mapping[str, RunnerAdapter] = MappingProxyType({
    runner.name: runner for runner in (
        ModuleRunner(GUI_RUNNER, "je_auto_control", optional=True),
        ModuleRunner("web-runner", "je_web_runner"),
        ModuleRunner("api-runner", "je_api_testka"),
        ModuleRunner("load-runner", "je_load_density"),
        ModuleRunner("file-runner", "automation_file"),
    )
})
RUNNER_NAMES: tuple[str, ...] = tuple(RUNNERS)
RUNNER_PACKAGES: Mapping[str, str] = MappingProxyType({name: runner.package for name, runner in RUNNERS.items()})

# Runners whose package comes from an extra (``test_pioneer[gui]``) instead of a core dependency.
OPTIONAL_RUNNERS: frozenset[str] = frozenset(name for name, runner in RUNNERS.items() if runner.optional)
