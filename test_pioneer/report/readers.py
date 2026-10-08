"""Read a runner's own report into TestPioneer's test cases.

Each runner format stays behind a reader; the rest of TestPioneer only sees ``CaseResult``.
The four runners that report (web, API, load, GUI) share one layout: a pair of files,
``<name>_success.json`` and ``<name>_failure.json``, each an object that maps ``Success_Test1``,
``Failure_Test1``, ... to a record of strings. Only the field names differ per runner.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from test_pioneer.models.result import CaseResult, Status

SUCCESS_SUFFIX = "_success.json"
FAILURE_SUFFIX = "_failure.json"
# A report with full response bodies can be large; beyond this it is left unread.
MAX_REPORT_BYTES = 50 * 1024 * 1024
_MAX_NAME = 200
_MAX_MESSAGE = 2000
_EMPTY = (None, "", "None")


@dataclass(frozen=True)
class ParsedReport:
    """The cases found in a runner's artifact directory and the raw report they came from.

    ``keys`` holds one fingerprint per case, of the record it was made from, so that a record
    repeated by a later report can be recognised.
    """

    cases: list[CaseResult]
    source: Path
    keys: list[str] = field(default_factory=list)


class ReportReader(Protocol):  # pylint: disable=too-few-public-methods  # a protocol of one method
    """Turns the report files in a runner's artifact directory into test cases."""

    def read(self, directory: Path) -> ParsedReport | None:
        """Return the cases found below ``directory``, or ``None`` when there is no report.

        Raises ``OSError`` or ``ValueError`` for a report that cannot be read or is malformed.
        """


def _shorten(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


def _malformed(path: Path, problem: str) -> ValueError:
    """Build the error for a report that does not have the expected layout."""
    return ValueError(f"{path.name}{problem}")


def _fingerprint(record: dict[str, object]) -> str:
    """Identify a record by its content."""
    return hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _load_records(path: Path) -> Iterator[tuple[str, dict[str, object]]]:
    """Yield each ``(key, record)`` of one report file."""
    if path.stat().st_size > MAX_REPORT_BYTES:
        raise _malformed(path, f" is larger than {MAX_REPORT_BYTES} bytes")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise _malformed(path, " is not a JSON object")
    for key, record in data.items():
        if not isinstance(record, dict):
            raise _malformed(path, f": {key} is not a record")
        yield str(key), record


@dataclass(frozen=True)
class RecordPairReader:
    """Reader of the ``*_success.json`` / ``*_failure.json`` pair that the je runners write.

    ``name_fields`` are the record fields that, joined, name a test; ``message_fields`` are tried
    in order for the reason of a failure.
    """

    name_fields: tuple[str, ...]
    message_fields: tuple[str, ...] = ("error", "exception")

    def read(self, directory: Path) -> ParsedReport | None:
        """Read every report pair below ``directory``; failures come first."""
        failures = sorted(directory.rglob(f"*{FAILURE_SUFFIX}"))
        successes = sorted(directory.rglob(f"*{SUCCESS_SUFFIX}"))
        if not failures and not successes:
            return None
        records = [(key, record, Status.FAILED) for path in failures for key, record in _load_records(path)]
        records += [(key, record, Status.PASSED) for path in successes for key, record in _load_records(path)]
        cases = [self._case(key, record, status) for key, record, status in records]
        failed = any(case.status is Status.FAILED for case in cases)
        source = (failures if failed and failures else successes or failures)[0]
        return ParsedReport(cases, source, [_fingerprint(record) for _key, record, _status in records])

    def _case(self, key: str, record: dict[str, object], status: Status) -> CaseResult:
        parts = [str(record[field]) for field in self.name_fields if record.get(field) not in _EMPTY]
        name = _shorten(" ".join(parts) or key, _MAX_NAME)
        if status is Status.PASSED:
            return CaseResult(name, status)
        reason = next((str(record[field]) for field in self.message_fields
                       if record.get(field) not in _EMPTY), None)
        return CaseResult(name, status, _shorten(reason, _MAX_MESSAGE) if reason is not None else None)


# The field names of each runner's records.
API_REPORT = RecordPairReader(("request_method", "http_method", "request_url", "test_url"))
LOAD_REPORT = RecordPairReader(("Method", "name"))
# Web and GUI records also carry the action's parameters, which may hold typed secrets: left out.
ACTION_REPORT = RecordPairReader(("function_name",))
