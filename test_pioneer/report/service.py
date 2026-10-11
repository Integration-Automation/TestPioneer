"""Write the consolidated report of a run.

``testpioneer-report.json`` is the canonical, machine-readable result; ``testpioneer-report.html``
is the same data for people; ``testpioneer-junit.xml`` is optional, for CI systems. The raw
runner reports stay in the run's artifact directory, and the HTML page links to them.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from pathlib import Path

from test_pioneer.models.result import RunResult
from test_pioneer.report.formats import FORMAT_HTML, FORMAT_JUNIT, REPORT_FILES
from test_pioneer.report.html_report import render_html
from test_pioneer.report.junit_report import render_junit


def _render(result: RunResult, report_format: str, directory: Path) -> str:
    """Render one of the known formats."""
    if report_format == FORMAT_HTML:
        return render_html(result, directory)
    if report_format == FORMAT_JUNIT:
        return render_junit(result)
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n"


def write_reports(result: RunResult, directory: Path, formats: Sequence[str]) -> list[Path]:
    """Write ``result`` into ``directory`` in each of ``formats`` and return the files written.

    The paths are also stored in ``result.reports`` first, so every report names its siblings.
    Raises ``OSError`` when a file cannot be written and ``ValueError`` for an unknown format.
    """
    unknown = [report_format for report_format in formats if report_format not in REPORT_FILES]
    if unknown:
        raise ValueError(f"unknown report format: {unknown[0]}")
    targets = [(report_format, directory / REPORT_FILES[report_format]) for report_format in dict.fromkeys(formats)]
    if not targets:
        return []
    result.reports = [str(path) for _format, path in targets]
    directory.mkdir(parents=True, exist_ok=True)
    for report_format, path in targets:
        path.write_text(_render(result, report_format, directory), encoding="utf-8", errors="backslashreplace")
    return [path for _format, path in targets]
