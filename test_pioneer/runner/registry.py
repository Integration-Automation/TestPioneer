"""The runners a workflow can name, and the adapter behind each one.

The JSON Schema, the linter and ``parallel_run`` all read this table, so a runner is declared once.
"""
from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from test_pioneer.report.readers import ACTION_REPORT, API_REPORT, LOAD_REPORT
from test_pioneer.runner.adapter import ModuleRunner, RunnerAdapter

GUI_RUNNER = "gui-runner"

RUNNERS: Mapping[str, RunnerAdapter] = MappingProxyType({
    runner.name: runner for runner in (
        ModuleRunner(GUI_RUNNER, "je_auto_control", optional=True, report=ACTION_REPORT),
        ModuleRunner("web-runner", "je_web_runner", report=ACTION_REPORT),
        ModuleRunner("api-runner", "je_api_testka", report=API_REPORT),
        ModuleRunner("load-runner", "je_load_density", report=LOAD_REPORT),
        # FileAutomation has no report generator.
        ModuleRunner("file-runner", "automation_file"),
    )
})
RUNNER_NAMES: tuple[str, ...] = tuple(RUNNERS)
RUNNER_PACKAGES: Mapping[str, str] = MappingProxyType({name: runner.package for name, runner in RUNNERS.items()})

# Runners whose package comes from an extra (``test_pioneer[gui]``) instead of a core dependency.
OPTIONAL_RUNNERS: frozenset[str] = frozenset(name for name, runner in RUNNERS.items() if runner.optional)


def find_runner(name: str) -> RunnerAdapter | None:
    """Return the adapter of a runner tag, or ``None`` for a tag that is not registered."""
    return RUNNERS.get(name)
