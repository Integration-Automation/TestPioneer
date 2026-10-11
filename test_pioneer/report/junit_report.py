"""Render a run result as JUnit XML, for CI systems that display it.

One ``<testsuite>`` per runner execution: its recorded tests when its report was read, otherwise
a single test for the script. Steps that are not runner steps form one more suite, so a failed
download or wait is not lost. The XML is written as text; nothing here parses XML.
"""
from __future__ import annotations

import html
import re

from test_pioneer.models.result import RunnerResult, RunResult, Status

_RUNNER_ACTIONS = ("run", "run_folder", "parallel_run")
# The code point ranges XML 1.0 allows besides tab, line feed and carriage return.
_ALLOWED_RANGES = ((0x20, 0xD7FF), (0xE000, 0xFFFD), (0x10000, 0x10FFFF))
# Every character outside them is invalid in XML 1.0, even escaped.
_INVALID = re.compile(
    "[^\t\n\r" + "".join(f"{chr(first)}-{chr(last)}" for first, last in _ALLOWED_RANGES) + "]")
# JUnit's timestamp is a date-time to the second with no zone; the result's times are UTC.
_DATE_TIME = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
# The element a status becomes inside a testcase; a passed test has none.
_ELEMENTS = {Status.FAILED: "failure", Status.ERROR: "error", Status.CANCELLED: "skipped"}

# name, status, message, duration in milliseconds
Case = tuple[str, Status, str | None, int]


def _text(value: object) -> str:
    """Escape a value for use in XML text or in a double-quoted attribute."""
    return html.escape(_INVALID.sub("?", str(value)), quote=True)


def _seconds(milliseconds: int) -> str:
    return f"{milliseconds / 1000:.3f}"


def _timestamp(moment: str) -> str:
    """Return the ``timestamp`` attribute for a start time such as ``2026-10-08T03:15:42.131Z``.

    The fraction and the ``Z`` are left out: several JUnit readers, among them
    ``datetime.fromisoformat`` before Python 3.11, do not accept them. No start time, no attribute.
    """
    match = _DATE_TIME.match(moment)
    return f' timestamp="{match.group(0)}"' if match else ""


def _testcase(classname: str, case: Case) -> list[str]:
    name, status, message, duration_ms = case
    opening = f'    <testcase classname="{_text(classname)}" name="{_text(name)}" time="{_seconds(duration_ms)}"'
    element = _ELEMENTS.get(status)
    if element is None:
        return [opening + "/>"]
    detail = f' message="{_text(message)}"' if message else ""
    return [opening + ">", f"      <{element}{detail}/>", "    </testcase>"]


def _suite(name: str, classname: str, cases: list[Case], duration_ms: int, started_at: str) -> list[str]:
    counts = {status: sum(1 for case in cases if case[1] is status) for status in _ELEMENTS}
    lines = [(
        f'  <testsuite name="{_text(name)}" tests="{len(cases)}" failures="{counts[Status.FAILED]}"'
        f' errors="{counts[Status.ERROR]}" skipped="{counts[Status.CANCELLED]}"'
        f' time="{_seconds(duration_ms)}"{_timestamp(started_at)}>'
    )]
    for case in cases:
        lines += _testcase(classname, case)
    lines.append("  </testsuite>")
    return lines


def _runner_cases(runner: RunnerResult) -> list[Case]:
    """The tests of one runner execution: what its report recorded, or the script as one test."""
    if runner.cases:
        return [(case.name, case.status, case.message, 0) for case in runner.cases]
    return [(runner.script, runner.status, runner.message, runner.duration_ms)]


def _step_cases(result: RunResult) -> list[Case]:
    cases: list[Case] = [(step.name, step.status, step.message, step.duration_ms)
                         for step in result.steps if step.action not in _RUNNER_ACTIONS]
    if result.message is not None:
        cases.append(("workflow", result.status, result.message, 0))
    return cases


def render_junit(result: RunResult) -> str:
    """Return the JUnit XML document of a run."""
    suites: list[str] = []
    total = failures = errors = 0
    for runner in result.runners:
        cases = _runner_cases(runner)
        suites += _suite(f"{runner.runner}: {runner.script}", runner.runner, cases,
                         runner.duration_ms, runner.started_at)
    step_cases = _step_cases(result)
    if step_cases:
        suites += _suite("workflow steps", "testpioneer", step_cases, 0, result.started_at)
    for cases in ([*map(_runner_cases, result.runners), step_cases]):
        total += len(cases)
        failures += sum(1 for case in cases if case[1] is Status.FAILED)
        errors += sum(1 for case in cases if case[1] is Status.ERROR)
    header = (f'<testsuites name="TestPioneer {_text(result.run_id)}" tests="{total}" failures="{failures}"'
              f' errors="{errors}" time="{_seconds(result.duration_ms)}">')
    return "\n".join(['<?xml version="1.0" encoding="UTF-8"?>', header, *suites, "</testsuites>"]) + "\n"
