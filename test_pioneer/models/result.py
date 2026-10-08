"""The normalized result of one workflow run.

This format belongs to TestPioneer. Each runner's own report stays behind an adapter and is
translated into these records; the run manifest and the merged report are written from them.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

RESULT_FORMAT_VERSION = "1.0"


class Status(str, Enum):
    """Outcome of a run, a step or a runner execution."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    CANCELLED = "cancelled"


# Later entries outrank earlier ones when statuses are combined.
_RANK = (Status.PASSED, Status.CANCELLED, Status.FAILED, Status.ERROR)


def worst_status(statuses: Iterable[Status]) -> Status:
    """Combine statuses into one: error over failed over cancelled over passed."""
    return max(statuses, key=_RANK.index, default=Status.PASSED)


def utc_now() -> str:
    """Return the current UTC time as ISO 8601, for example ``2026-10-08T03:15:42.123Z``."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class Artifact:
    """One file kept for a run; ``path`` is relative to the run's artifact directory."""

    path: str
    kind: str = "other"
    size: int = 0

    def to_dict(self) -> dict[str, object]:
        """Return the JSON form."""
        return {"path": self.path, "kind": self.kind, "size": self.size}


@dataclass
class RunnerResult:  # pylint: disable=too-many-instance-attributes  # one field per report key
    """One runner execution: a ``run`` or ``run_folder`` step, or one entry of ``parallel_run``."""

    runner: str
    script: str
    step: str
    status: Status
    exit_code: int | None = None
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    message: str | None = None
    artifact_dir: str | None = None
    report: str | None = None
    artifacts: list[Artifact] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        """Return the JSON form."""
        return {
            "runner": self.runner,
            "script": self.script,
            "step": self.step,
            "status": self.status.value,
            "exit_code": self.exit_code,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "message": self.message,
            "artifact_dir": self.artifact_dir,
            "report": self.report,
            "artifacts": [item.to_dict() for item in self.artifacts],
        }


@dataclass
class StepResult:
    """One workflow step, whatever its type."""

    name: str
    action: str
    status: Status
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    message: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return the JSON form."""
        return {
            "name": self.name,
            "action": self.action,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "message": self.message,
        }


@dataclass
class RunResult:  # pylint: disable=too-many-instance-attributes  # one field per report key
    """A whole workflow run, identified by ``run_id``."""

    run_id: str
    status: Status = Status.PASSED
    started_at: str = ""
    finished_at: str = ""
    duration_ms: int = 0
    workflow: str | None = None
    steps: list[StepResult] = field(default_factory=list)
    runners: list[RunnerResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def summary(self) -> dict[str, int]:
        """Count the runner executions by status, plus their total."""
        counts = {status.value: 0 for status in Status}
        for runner in self.runners:
            counts[runner.status.value] += 1
        counts["total"] = len(self.runners)
        return counts

    def to_dict(self) -> dict[str, object]:
        """Return the JSON form written to the manifest and the merged report."""
        return {
            "format_version": RESULT_FORMAT_VERSION,
            "run_id": self.run_id,
            "status": self.status.value,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "workflow": self.workflow,
            "summary": self.summary(),
            "steps": [step.to_dict() for step in self.steps],
            "runners": [runner.to_dict() for runner in self.runners],
            "warnings": list(self.warnings),
        }
