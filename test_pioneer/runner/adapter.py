"""The contract between TestPioneer and a runner package.

A runner is started as ``python -m <package> --execute_file <script>`` and is told where its
artifacts belong through two environment variables (``test_pioneer.artifacts.context``). A runner
that does not read them yet is still wrapped: TestPioneer keeps its console output and its exit
code in the artifact directory for it. Native support can then be added to one runner at a time.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from test_pioneer.report.readers import ReportReader


class RunnerAdapter(Protocol):
    """What TestPioneer needs to know about a runner to start it and to read what it reports."""

    @property
    def name(self) -> str:
        """The ``with:`` tag a workflow uses for this runner."""

    @property
    def package(self) -> str:
        """The importable package that implements the runner."""

    @property
    def optional(self) -> bool:
        """True when the package comes from an extra instead of a core dependency."""

    @property
    def report(self) -> ReportReader | None:
        """Reader of the runner's own report format, or ``None`` when it writes no report."""

    def command(self, executor: str, script: Path) -> list[str]:
        """Return the argument list that runs ``script`` in a sub-process of ``executor``."""


@dataclass(frozen=True)
class ModuleRunner:
    """A runner package with the family's ``--execute_file`` command line.

    ``optional`` marks a package that comes from an extra instead of a core dependency.
    ``report`` reads the report files the runner leaves in its artifact directory.
    """

    name: str
    package: str
    optional: bool = False
    report: ReportReader | None = None

    def command(self, executor: str, script: Path) -> list[str]:
        """Return ``[executor, "-m", package, "--execute_file", script]``."""
        return [executor, "-m", self.package, "--execute_file", str(script)]
