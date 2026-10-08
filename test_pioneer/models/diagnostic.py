"""Structured validation diagnostics.

The schema validator, the linter and the ``validate`` command all report problems as
``Diagnostic`` objects, so a UI can show them without parsing log text.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

YamlPath = tuple[str | int, ...]


class Severity(str, Enum):
    """How serious a diagnostic is; only errors make a workflow invalid."""

    ERROR = "error"
    WARNING = "warning"


def format_path(path: YamlPath) -> str:
    """Render a YAML path as ``jobs.steps[0].with``; the document root is ``<root>``."""
    text = ""
    for part in path:
        if isinstance(part, int):
            text += f"[{part}]"
        else:
            text += f".{part}" if text else part
    return text or "<root>"


@dataclass(frozen=True)
class Diagnostic:
    """One problem in a workflow, located by YAML path and 1-based line and column."""

    severity: Severity
    code: str
    message: str
    path: YamlPath = ()
    line: int | None = None
    column: int | None = None
    source: str = "lint"

    def to_dict(self) -> dict[str, object]:
        """Return the JSON form used by ``validate --format json``."""
        return {
            "severity": self.severity.value,
            "code": self.code,
            "message": self.message,
            "path": list(self.path),
            "pointer": format_path(self.path),
            "line": self.line,
            "column": self.column,
            "source": self.source,
        }


@dataclass(frozen=True)
class ValidationResult:
    """Every diagnostic found in one workflow, in document order."""

    diagnostics: tuple[Diagnostic, ...] = ()
    source: str | None = None

    @property
    def errors(self) -> tuple[Diagnostic, ...]:
        """The diagnostics that make the workflow invalid."""
        return tuple(item for item in self.diagnostics if item.severity is Severity.ERROR)

    @property
    def warnings(self) -> tuple[Diagnostic, ...]:
        """The diagnostics that do not make the workflow invalid."""
        return tuple(item for item in self.diagnostics if item.severity is Severity.WARNING)

    @property
    def ok(self) -> bool:
        """True when there is no error; warnings do not count."""
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        """Return the JSON form used by ``validate --format json``."""
        return {
            "source": self.source,
            "ok": self.ok,
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "diagnostics": [item.to_dict() for item in self.diagnostics],
        }
