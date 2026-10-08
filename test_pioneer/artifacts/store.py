"""The directory tree of one run.

.. code-block:: text

   <root>/<run-id>/
     runners/<runner>/<nn>-<step>/   one directory per runner execution
     testpioneer/execution.log       what TestPioneer itself logged
     testpioneer/manifest.json       the run result, written when the run ends
"""
from __future__ import annotations

import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

from test_pioneer.artifacts.context import slug
from test_pioneer.models.result import Artifact, RunResult

RUNNERS_DIR = "runners"
ENGINE_DIR = "testpioneer"
EXECUTION_LOG = "execution.log"
MANIFEST = "manifest.json"

_KINDS: dict[str, str] = {
    **dict.fromkeys((".log", ".txt", ".out", ".err"), "log"),
    **dict.fromkeys((".json", ".xml", ".html", ".htm", ".csv"), "report"),
    **dict.fromkeys((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"), "screenshot"),
    **dict.fromkeys((".mp4", ".avi", ".mkv", ".webm", ".mov"), "video"),
    **dict.fromkeys((".har", ".trace", ".zip"), "trace"),
}


def artifact_kind(path: Path) -> str:
    """Classify a file by its extension: log, report, screenshot, video, trace or other."""
    return _KINDS.get(path.suffix.lower(), "other")


def _files(directory: Path) -> Iterator[Path]:
    """Yield every file below ``directory``, in a stable order."""
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            yield path


class ArtifactStore:
    """Creates, lists and removes the files of one run below ``<root>/<run-id>``."""

    def __init__(self, root: Path, run_id: str) -> None:
        self.run_dir = Path(root) / run_id
        self.engine_dir = self.run_dir / ENGINE_DIR
        self._sequence = 0
        # The directories above the run directory that this run had to create, nearest first.
        self._created: list[Path] = []
        self._log: TextIO | None = None

    @property
    def execution_log(self) -> Path:
        """Path of TestPioneer's own log for this run."""
        return self.engine_dir / EXECUTION_LOG

    @property
    def manifest(self) -> Path:
        """Path of the run manifest."""
        return self.engine_dir / MANIFEST

    def create(self) -> None:
        """Create the run directory; raises ``OSError`` when the location is not writable."""
        root = self.run_dir.parent
        self._created = [directory for directory in (root, *root.parents) if not directory.exists()]
        self.engine_dir.mkdir(parents=True, exist_ok=True)
        self._log = self.execution_log.open("w", encoding="utf-8", errors="backslashreplace")

    def log(self, line: str) -> None:
        """Append a line to the execution log; raises ``OSError`` when it cannot be written."""
        if self._log is not None:
            self._log.write(line + "\n")
            self._log.flush()

    def close_log(self) -> None:
        """Close the execution log; later lines are dropped."""
        log, self._log = self._log, None
        if log is not None:
            log.close()

    def new_runner_dir(self, runner: str, label: str) -> Path:
        """Create and return the directory of the next runner execution."""
        self._sequence += 1
        name = f"{self._sequence:02d}-{slug(label, 'step')}"
        directory = self.run_dir / RUNNERS_DIR / slug(runner, "runner") / name
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    def relative(self, path: Path) -> str:
        """Return ``path`` relative to the run directory, with forward slashes."""
        return path.relative_to(self.run_dir).as_posix()

    def collect(self, directory: Path) -> list[Artifact]:
        """List every file below ``directory`` as an artifact of this run."""
        return [Artifact(self.relative(path), artifact_kind(path), path.stat().st_size)
                for path in _files(directory)]

    def write_manifest(self, result: RunResult) -> None:
        """Write the run result as ``testpioneer/manifest.json``."""
        text = json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n"
        self.manifest.write_text(text, encoding="utf-8")

    def remove(self, directory: Path) -> None:
        """Delete a directory of this run, then the parents it leaves empty.

        A path outside the run directory is refused.
        """
        target = directory.resolve()
        base = self.run_dir.resolve()
        if base not in target.parents:
            raise ValueError(f"not inside the run directory: {directory}")
        shutil.rmtree(target)
        parent = target.parent
        while parent != base and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent

    def remove_run(self) -> None:
        """Delete the whole run directory, and the directories this run created to hold it."""
        self.close_log()
        shutil.rmtree(self.run_dir)
        for directory in self._created:
            if any(directory.iterdir()):
                break
            directory.rmdir()
