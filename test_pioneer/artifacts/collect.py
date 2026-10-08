"""Collect the files a step declares with ``artifacts:`` into its runner's artifact directory.

The runner packages write their reports and screenshots relative to the working directory. Until
they write into ``TEST_PIONEER_ARTIFACT_DIR`` themselves, a step names what its runner produces
and TestPioneer copies it. Only files changed since the runner started are taken, so a report
left by an earlier run is never mistaken for this one's.
"""
from __future__ import annotations

import shutil
from collections.abc import Iterator, Sequence
from pathlib import Path

COLLECTED_DIR = "collected"
# Coarse file systems store modification times in steps of up to two seconds.
_MTIME_SLACK = 2.0


def as_patterns(value: object) -> tuple[str, ...]:
    """Return the ``artifacts`` value of a step as patterns; anything but a list of strings is empty."""
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(str(item) for item in value)
    return ()


def _inside(path: Path, directory: Path) -> bool:
    return path == directory or directory in path.parents


def pattern_refusal(pattern: str) -> str | None:
    """Say why a pattern may not be used, or return ``None`` when it may."""
    path = Path(pattern)
    if not pattern.strip():
        return "it is empty"
    if path.is_absolute() or path.drive or pattern.startswith(("/", "\\")):
        return "it is not relative to the working directory"
    if ".." in path.parts:
        return "it leaves the working directory"
    return None


def _matching_files(base: Path, pattern: str) -> Iterator[Path]:
    """Yield the files a pattern matches; a matched directory stands for every file below it."""
    for match in sorted(base.glob(pattern)):
        if match.is_dir():
            yield from (path for path in sorted(match.rglob("*")) if path.is_file())
        elif match.is_file():
            yield match


def _copy_new(base: Path, pattern: str, destination: Path, since: float) -> int:
    """Copy the files of one pattern that changed after ``since``; return how many were copied."""
    copied = 0
    root = base.resolve()
    # runners/<runner>/<nn>-<step> below the run directory, whose files are never collected again.
    run_dir = destination.resolve().parents[2]
    for source in _matching_files(base, pattern):
        resolved = source.resolve()
        # A link may point outside the working directory even though the pattern does not.
        if not _inside(resolved, root) or _inside(resolved, run_dir):
            continue
        if source.stat().st_mtime < since - _MTIME_SLACK:
            continue
        target = destination / COLLECTED_DIR / source.relative_to(base)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied += 1
    return copied


def collect_files(patterns: Sequence[str], destination: Path, since: float) -> list[str]:
    """Copy what ``patterns`` match below the working directory into ``destination/collected``.

    ``since`` is the wall-clock time the runner started. The return value lists what went wrong,
    as warnings: a refused pattern, a pattern that matched nothing new, a file that could not be
    copied. Nothing is raised.
    """
    warnings: list[str] = []
    base = Path.cwd()
    for pattern in patterns:
        refusal = pattern_refusal(pattern)
        if refusal is not None:
            warnings.append(f"artifact pattern {pattern!r} is not used: {refusal}")
            continue
        try:
            if _copy_new(base, pattern, destination, since) == 0:
                warnings.append(f"artifact pattern {pattern!r} matched no file written by this runner")
        except (OSError, ValueError) as error:
            warnings.append(f"artifact pattern {pattern!r} could not be collected: {error}")
    return warnings
