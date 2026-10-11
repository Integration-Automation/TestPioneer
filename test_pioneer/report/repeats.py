"""Tell the records a runner already reported in this process from the new ones.

A runner package keeps one list of records per process, and its report writes the whole list.
``run`` and ``run_folder`` call the runner inside the TestPioneer process, so every later report
of the same runner starts with the records of the earlier calls. Those are dropped here: a test
is counted, and a failure is blamed, only for the call that recorded it.

A report that does not start with the earlier records means the script cleared them, and then
every record in it is new.
"""
from __future__ import annotations

from test_pioneer.models.result import CaseResult, Status
from test_pioneer.report.readers import ParsedReport


class RepeatFilter:
    """Remembers, per runner, the records of its last in-process report."""

    def __init__(self) -> None:
        # runner -> (keys of the failed records, keys of the passed records), in report order
        self._reported: dict[str, tuple[list[str], list[str]]] = {}

    def new_cases(self, runner: str, report: ParsedReport) -> list[CaseResult]:
        """Return the cases of ``report`` that an earlier report of ``runner`` did not hold."""
        pairs = list(zip(report.cases, report.keys))
        groups = (
            [pair for pair in pairs if pair[0].status is not Status.PASSED],
            [pair for pair in pairs if pair[0].status is Status.PASSED],
        )
        keys = ([key for _case, key in groups[0]], [key for _case, key in groups[1]])
        earlier = self._reported.get(runner, ([], []))
        self._reported[runner] = keys
        if any(current[:len(old)] != old for current, old in zip(keys, earlier)):
            return list(report.cases)
        return [case for group, old in zip(groups, earlier) for case, _key in group[len(old):]]

    def reset(self) -> None:
        """Forget every report, as after the runners' records were cleared."""
        self._reported.clear()


# One per process, like the record lists of the runner packages it mirrors.
in_process_records = RepeatFilter()
